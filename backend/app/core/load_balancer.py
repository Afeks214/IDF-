#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Load Balancing and Auto-Scaling Infrastructure for IDF Testing System
Supports multiple load balancing strategies and auto-scaling policies
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog
from contextlib import asynccontextmanager
import hashlib
import json

from core.config import settings
from core.performance_monitor import performance_monitor

logger = structlog.get_logger()


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"


class HealthStatus(Enum):
    """Server health status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    MAINTENANCE = "maintenance"


@dataclass
class ServerNode:
    """Server node configuration"""
    id: str
    host: str
    port: int
    weight: int = 100
    max_connections: int = 100
    current_connections: int = 0
    health_status: HealthStatus = HealthStatus.HEALTHY
    response_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_health_check: float = 0.0
    failure_count: int = 0
    total_requests: int = 0
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"
    
    @property
    def is_available(self) -> bool:
        return (self.health_status == HealthStatus.HEALTHY and 
                self.current_connections < self.max_connections)
    
    def update_metrics(self, response_time: float, cpu_usage: float, memory_usage: float):
        """Update server metrics"""
        self.response_time = response_time
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.last_health_check = time.time()


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    health_check_interval: int = 30
    health_check_timeout: int = 5
    max_failure_count: int = 3
    failure_reset_time: int = 300  # 5 minutes
    sticky_sessions: bool = False
    session_timeout: int = 3600  # 1 hour
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


class SessionManager:
    """Session management for sticky sessions"""
    
    def __init__(self, timeout: int = 3600):
        self.sessions = {}
        self.timeout = timeout
    
    def get_server_for_session(self, session_id: str) -> Optional[str]:
        """Get server for session"""
        if session_id in self.sessions:
            session_data = self.sessions[session_id]
            if time.time() - session_data["created"] < self.timeout:
                return session_data["server_id"]
            else:
                del self.sessions[session_id]
        return None
    
    def create_session(self, session_id: str, server_id: str):
        """Create new session"""
        self.sessions[session_id] = {
            "server_id": server_id,
            "created": time.time()
        }
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, data in self.sessions.items()
            if current_time - data["created"] > self.timeout
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]


class CircuitBreaker:
    """Circuit breaker for server protection"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        """Call function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e


class LoadBalancer:
    """Advanced load balancer with multiple strategies"""
    
    def __init__(self, config: LoadBalancerConfig):
        self.config = config
        self.servers: List[ServerNode] = []
        self.session_manager = SessionManager(config.session_timeout)
        self.circuit_breakers = {}
        self.current_index = 0
        self.health_check_task = None
        self.running = False
        
        # Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.avg_response_time = 0.0
    
    def add_server(self, server: ServerNode):
        """Add server to load balancer"""
        self.servers.append(server)
        if self.config.enable_circuit_breaker:
            self.circuit_breakers[server.id] = CircuitBreaker(
                self.config.circuit_breaker_threshold,
                self.config.circuit_breaker_timeout
            )
        logger.info(f"Added server to load balancer: {server.address}")
    
    def remove_server(self, server_id: str):
        """Remove server from load balancer"""
        self.servers = [s for s in self.servers if s.id != server_id]
        if server_id in self.circuit_breakers:
            del self.circuit_breakers[server_id]
        logger.info(f"Removed server from load balancer: {server_id}")
    
    async def start(self):
        """Start load balancer"""
        if self.running:
            return
        
        self.running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Load balancer started")
    
    async def stop(self):
        """Stop load balancer"""
        self.running = False
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("Load balancer stopped")
    
    async def get_server(self, client_ip: str = None, session_id: str = None) -> Optional[ServerNode]:
        """Get server based on load balancing strategy"""
        available_servers = [s for s in self.servers if s.is_available]
        
        if not available_servers:
            logger.warning("No available servers")
            return None
        
        # Check for sticky sessions
        if self.config.sticky_sessions and session_id:
            server_id = self.session_manager.get_server_for_session(session_id)
            if server_id:
                server = next((s for s in available_servers if s.id == server_id), None)
                if server:
                    return server
        
        # Apply load balancing strategy
        if self.config.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            server = self._round_robin_select(available_servers)
        elif self.config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            server = self._least_connections_select(available_servers)
        elif self.config.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            server = self._weighted_round_robin_select(available_servers)
        elif self.config.strategy == LoadBalancingStrategy.IP_HASH:
            server = self._ip_hash_select(available_servers, client_ip)
        elif self.config.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            server = self._least_response_time_select(available_servers)
        elif self.config.strategy == LoadBalancingStrategy.RESOURCE_BASED:
            server = self._resource_based_select(available_servers)
        else:
            server = self._round_robin_select(available_servers)
        
        # Create session if sticky sessions are enabled
        if self.config.sticky_sessions and session_id and server:
            self.session_manager.create_session(session_id, server.id)
        
        return server
    
    def _round_robin_select(self, servers: List[ServerNode]) -> ServerNode:
        """Round-robin server selection"""
        if not servers:
            return None
        
        server = servers[self.current_index % len(servers)]
        self.current_index += 1
        return server
    
    def _least_connections_select(self, servers: List[ServerNode]) -> ServerNode:
        """Least connections server selection"""
        return min(servers, key=lambda s: s.current_connections)
    
    def _weighted_round_robin_select(self, servers: List[ServerNode]) -> ServerNode:
        """Weighted round-robin server selection"""
        total_weight = sum(s.weight for s in servers)
        if total_weight == 0:
            return self._round_robin_select(servers)
        
        # Create weighted list
        weighted_servers = []
        for server in servers:
            weighted_servers.extend([server] * server.weight)
        
        if not weighted_servers:
            return self._round_robin_select(servers)
        
        server = weighted_servers[self.current_index % len(weighted_servers)]
        self.current_index += 1
        return server
    
    def _ip_hash_select(self, servers: List[ServerNode], client_ip: str) -> ServerNode:
        """IP hash server selection"""
        if not client_ip:
            return self._round_robin_select(servers)
        
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        return servers[hash_value % len(servers)]
    
    def _least_response_time_select(self, servers: List[ServerNode]) -> ServerNode:
        """Least response time server selection"""
        return min(servers, key=lambda s: s.response_time)
    
    def _resource_based_select(self, servers: List[ServerNode]) -> ServerNode:
        """Resource-based server selection"""
        # Calculate resource score (lower is better)
        def resource_score(server):
            cpu_score = server.cpu_usage / 100
            memory_score = server.memory_usage / 100
            connection_score = server.current_connections / server.max_connections
            response_score = min(server.response_time / 1000, 1.0)  # Normalize to 0-1
            
            return cpu_score + memory_score + connection_score + response_score
        
        return min(servers, key=resource_score)
    
    async def _health_check_loop(self):
        """Health check loop"""
        while self.running:
            try:
                await self._perform_health_checks()
                self.session_manager.cleanup_expired_sessions()
                await asyncio.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error("Health check loop error", error=str(e))
                await asyncio.sleep(self.config.health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all servers"""
        for server in self.servers:
            try:
                # Simple health check (would be replaced with actual HTTP check)
                await self._check_server_health(server)
                
                # Reset failure count on successful health check
                if server.health_status == HealthStatus.HEALTHY:
                    server.failure_count = 0
                
            except Exception as e:
                server.failure_count += 1
                logger.warning(f"Health check failed for server {server.id}", error=str(e))
                
                if server.failure_count >= self.config.max_failure_count:
                    server.health_status = HealthStatus.UNHEALTHY
                    logger.error(f"Server {server.id} marked as unhealthy")
    
    async def _check_server_health(self, server: ServerNode):
        """Check individual server health"""
        # This would be replaced with actual health check implementation
        # For now, simulate a basic check
        start_time = time.time()
        
        # Simulate health check
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Update metrics
        response_time = time.time() - start_time
        server.update_metrics(response_time, random.uniform(10, 80), random.uniform(20, 90))
        
        # Mark as healthy if within acceptable parameters
        if server.cpu_usage < 90 and server.memory_usage < 90:
            server.health_status = HealthStatus.HEALTHY
        else:
            server.health_status = HealthStatus.UNHEALTHY
    
    async def record_request(self, server: ServerNode, success: bool, response_time: float):
        """Record request metrics"""
        self.total_requests += 1
        server.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Update average response time
        if self.total_requests > 0:
            self.avg_response_time = ((self.avg_response_time * (self.total_requests - 1)) + response_time) / self.total_requests
        
        # Update server metrics
        server.update_metrics(response_time, server.cpu_usage, server.memory_usage)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / max(self.total_requests, 1)) * 100,
            "avg_response_time": self.avg_response_time,
            "active_servers": len([s for s in self.servers if s.health_status == HealthStatus.HEALTHY]),
            "total_servers": len(self.servers),
            "servers": [
                {
                    "id": s.id,
                    "address": s.address,
                    "health_status": s.health_status.value,
                    "current_connections": s.current_connections,
                    "max_connections": s.max_connections,
                    "response_time": s.response_time,
                    "cpu_usage": s.cpu_usage,
                    "memory_usage": s.memory_usage,
                    "total_requests": s.total_requests
                }
                for s in self.servers
            ]
        }


class AutoScaler:
    """Auto-scaling system for server management"""
    
    def __init__(self, load_balancer: LoadBalancer):
        self.load_balancer = load_balancer
        self.min_servers = 2
        self.max_servers = 10
        self.target_cpu_usage = 70
        self.target_memory_usage = 80
        self.target_response_time = 1.0
        self.scale_up_threshold = 80
        self.scale_down_threshold = 30
        self.scale_up_cooldown = 300  # 5 minutes
        self.scale_down_cooldown = 600  # 10 minutes
        self.last_scale_action = 0
        self.scaling_enabled = True
        self.scaling_task = None
        self.running = False
    
    async def start(self):
        """Start auto-scaler"""
        if self.running:
            return
        
        self.running = True
        self.scaling_task = asyncio.create_task(self._scaling_loop())
        logger.info("Auto-scaler started")
    
    async def stop(self):
        """Stop auto-scaler"""
        self.running = False
        if self.scaling_task:
            self.scaling_task.cancel()
            try:
                await self.scaling_task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-scaler stopped")
    
    async def _scaling_loop(self):
        """Main scaling loop"""
        while self.running:
            try:
                if self.scaling_enabled:
                    await self._evaluate_scaling()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error("Auto-scaling loop error", error=str(e))
                await asyncio.sleep(60)
    
    async def _evaluate_scaling(self):
        """Evaluate if scaling is needed"""
        healthy_servers = [s for s in self.load_balancer.servers if s.health_status == HealthStatus.HEALTHY]
        
        if not healthy_servers:
            return
        
        # Calculate average metrics
        avg_cpu = sum(s.cpu_usage for s in healthy_servers) / len(healthy_servers)
        avg_memory = sum(s.memory_usage for s in healthy_servers) / len(healthy_servers)
        avg_response_time = sum(s.response_time for s in healthy_servers) / len(healthy_servers)
        
        current_time = time.time()
        
        # Check if we need to scale up
        if (len(healthy_servers) < self.max_servers and 
            (avg_cpu > self.scale_up_threshold or 
             avg_memory > self.scale_up_threshold or 
             avg_response_time > self.target_response_time) and
            current_time - self.last_scale_action > self.scale_up_cooldown):
            
            await self._scale_up()
            self.last_scale_action = current_time
        
        # Check if we need to scale down
        elif (len(healthy_servers) > self.min_servers and 
              avg_cpu < self.scale_down_threshold and 
              avg_memory < self.scale_down_threshold and
              avg_response_time < self.target_response_time and
              current_time - self.last_scale_action > self.scale_down_cooldown):
            
            await self._scale_down()
            self.last_scale_action = current_time
    
    async def _scale_up(self):
        """Scale up by adding a new server"""
        # This would integrate with cloud provider APIs
        # For now, simulate by adding a new server
        
        server_id = f"server_{len(self.load_balancer.servers) + 1}"
        new_server = ServerNode(
            id=server_id,
            host="localhost",
            port=8000 + len(self.load_balancer.servers),
            weight=100,
            max_connections=100
        )
        
        self.load_balancer.add_server(new_server)
        logger.info(f"Scaled up: Added server {server_id}")
    
    async def _scale_down(self):
        """Scale down by removing a server"""
        # Find server with least connections
        healthy_servers = [s for s in self.load_balancer.servers if s.health_status == HealthStatus.HEALTHY]
        
        if len(healthy_servers) <= self.min_servers:
            return
        
        # Remove server with least connections
        server_to_remove = min(healthy_servers, key=lambda s: s.current_connections)
        
        # Mark server as draining first
        server_to_remove.health_status = HealthStatus.DRAINING
        
        # Wait for connections to drain (simplified)
        await asyncio.sleep(30)
        
        # Remove server
        self.load_balancer.remove_server(server_to_remove.id)
        logger.info(f"Scaled down: Removed server {server_to_remove.id}")
    
    def get_scaling_metrics(self) -> Dict[str, Any]:
        """Get auto-scaling metrics"""
        healthy_servers = [s for s in self.load_balancer.servers if s.health_status == HealthStatus.HEALTHY]
        
        if not healthy_servers:
            return {
                "enabled": self.scaling_enabled,
                "healthy_servers": 0,
                "avg_cpu": 0,
                "avg_memory": 0,
                "avg_response_time": 0,
                "last_scale_action": self.last_scale_action
            }
        
        return {
            "enabled": self.scaling_enabled,
            "healthy_servers": len(healthy_servers),
            "min_servers": self.min_servers,
            "max_servers": self.max_servers,
            "avg_cpu": sum(s.cpu_usage for s in healthy_servers) / len(healthy_servers),
            "avg_memory": sum(s.memory_usage for s in healthy_servers) / len(healthy_servers),
            "avg_response_time": sum(s.response_time for s in healthy_servers) / len(healthy_servers),
            "last_scale_action": self.last_scale_action,
            "scale_up_threshold": self.scale_up_threshold,
            "scale_down_threshold": self.scale_down_threshold
        }


# Global load balancer instance
load_balancer_config = LoadBalancerConfig(
    strategy=LoadBalancingStrategy.RESOURCE_BASED,
    health_check_interval=30,
    sticky_sessions=True,
    enable_circuit_breaker=True
)

load_balancer = LoadBalancer(load_balancer_config)
auto_scaler = AutoScaler(load_balancer)


@asynccontextmanager
async def load_balancer_context():
    """Context manager for load balancer"""
    await load_balancer.start()
    await auto_scaler.start()
    try:
        yield load_balancer
    finally:
        await auto_scaler.stop()
        await load_balancer.stop()


# Initialize default servers
async def initialize_load_balancer():
    """Initialize load balancer with default servers"""
    # Add primary server
    primary_server = ServerNode(
        id="primary",
        host="localhost",
        port=8000,
        weight=100,
        max_connections=100
    )
    
    load_balancer.add_server(primary_server)
    
    # Start load balancer
    await load_balancer.start()
    await auto_scaler.start()
    
    logger.info("Load balancer initialized with primary server")


# Cleanup function
async def cleanup_load_balancer():
    """Cleanup load balancer resources"""
    await auto_scaler.stop()
    await load_balancer.stop()
    logger.info("Load balancer cleanup completed")