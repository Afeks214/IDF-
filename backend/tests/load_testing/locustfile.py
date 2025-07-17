#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Load Testing with Locust
Comprehensive load testing scenarios for performance validation
"""

import json
import random
import time
from typing import Dict, List
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data for Hebrew processing
HEBREW_TEST_DATA = {
    "test_names": [
        "בדיקת מערכת תקשורת",
        "בדיקת רדיו VHF",
        "בדיקת הצפנה",
        "בדיקת מערכת ניווט",
        "בדיקת תדרים",
        "בדיקת אנטנות",
        "בדיקת מערכת פיקוד",
        "בדיקת רשת תקשורת",
        "בדיקת סיסמאות",
        "בדיקת אבטחת מידע"
    ],
    "descriptions": [
        "בדיקה מקיפה של מערכת התקשורת הצבאית",
        "בדיקת תדרי VHF במערכת הרדיו",
        "בדיקת מערכות ההצפנה והאבטחה",
        "בדיקת מערכת הניווט והמיקום",
        "בדיקת תדרי התקשורת והאות",
        "בדיקת ביצועי האנטנות והקליטה",
        "בדיקת מערכת הפיקוד והבקרה",
        "בדיקת רשת התקשורת הפנימית",
        "בדיקת מערכת הסיסמאות והאימות",
        "בדיקת אבטחת המידע והמערכות"
    ],
    "categories": [
        "תקשורת", "רדיו", "אבטחה", "ניווט", "תדרים", 
        "אנטנות", "פיקוד", "רשת", "אימות", "מידע"
    ],
    "statuses": ["active", "pending", "completed", "failed"]
}

# Performance tracking
response_times = []
error_counts = {"total": 0, "by_endpoint": {}}


class PerformanceTracker:
    """Track performance metrics during load testing"""
    
    def __init__(self):
        self.metrics = {
            "response_times": [],
            "error_rates": {},
            "throughput": 0,
            "concurrent_users": 0
        }
    
    def record_response_time(self, endpoint: str, response_time: float):
        """Record response time for analysis"""
        self.metrics["response_times"].append({
            "endpoint": endpoint,
            "time": response_time,
            "timestamp": time.time()
        })
    
    def record_error(self, endpoint: str, error_type: str):
        """Record error for analysis"""
        if endpoint not in self.metrics["error_rates"]:
            self.metrics["error_rates"][endpoint] = {}
        
        if error_type not in self.metrics["error_rates"][endpoint]:
            self.metrics["error_rates"][endpoint][error_type] = 0
        
        self.metrics["error_rates"][endpoint][error_type] += 1
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        if not self.metrics["response_times"]:
            return {"status": "no_data"}
        
        times = [m["time"] for m in self.metrics["response_times"]]
        
        return {
            "avg_response_time": sum(times) / len(times),
            "max_response_time": max(times),
            "min_response_time": min(times),
            "total_requests": len(times),
            "error_rate": sum(
                sum(errors.values()) 
                for errors in self.metrics["error_rates"].values()
            ) / len(times) if times else 0
        }


# Global performance tracker
performance_tracker = PerformanceTracker()


class BaseIDFUser(HttpUser):
    """Base user class for IDF testing scenarios"""
    
    abstract = True
    
    def on_start(self):
        """Called when user starts"""
        logger.info(f"Starting user session: {self.__class__.__name__}")
        self.session_data = {}
    
    def on_stop(self):
        """Called when user stops"""
        logger.info(f"Stopping user session: {self.__class__.__name__}")
    
    def get_random_hebrew_data(self) -> Dict:
        """Generate random Hebrew test data"""
        return {
            "name": random.choice(HEBREW_TEST_DATA["test_names"]),
            "description": random.choice(HEBREW_TEST_DATA["descriptions"]),
            "category": random.choice(HEBREW_TEST_DATA["categories"]),
            "status": random.choice(HEBREW_TEST_DATA["statuses"]),
            "test_date": time.strftime("%Y-%m-%d"),
            "test_id": random.randint(1000, 9999)
        }


class CasualUser(BaseIDFUser):
    """Simulates casual user behavior with moderate load"""
    
    weight = 3
    wait_time = between(2, 8)  # 2-8 seconds between requests
    
    @task(5)
    def view_health(self):
        """Check application health"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                performance_tracker.record_response_time("/health", response.elapsed.total_seconds())
            else:
                response.failure(f"Health check failed with status {response.status_code}")
                performance_tracker.record_error("/health", f"status_{response.status_code}")
    
    @task(3)
    def view_root(self):
        """Access root endpoint"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                performance_tracker.record_response_time("/", response.elapsed.total_seconds())
            else:
                response.failure(f"Root endpoint failed with status {response.status_code}")
                performance_tracker.record_error("/", f"status_{response.status_code}")
    
    @task(2)
    def view_docs(self):
        """Access API documentation"""
        with self.client.get("/api/v1/docs", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                performance_tracker.record_response_time("/api/v1/docs", response.elapsed.total_seconds())
            else:
                response.failure(f"Docs failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/docs", f"status_{response.status_code}")


class PowerUser(BaseIDFUser):
    """Simulates power user behavior with higher API usage"""
    
    weight = 2
    wait_time = between(1, 3)  # 1-3 seconds between requests
    
    @task(4)
    def api_operations(self):
        """Perform typical API operations"""
        # This would be expanded when actual API endpoints are implemented
        endpoints = ["/health", "/", "/api/v1/docs"]
        endpoint = random.choice(endpoints)
        
        with self.client.get(endpoint, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
                performance_tracker.record_response_time(endpoint, response.elapsed.total_seconds())
            else:
                response.failure(f"API operation failed with status {response.status_code}")
                performance_tracker.record_error(endpoint, f"status_{response.status_code}")
    
    @task(2)
    def hebrew_data_processing(self):
        """Simulate Hebrew data processing"""
        test_data = self.get_random_hebrew_data()
        
        # Simulate data processing endpoint (when implemented)
        with self.client.post(
            "/api/v1/process-data",
            json=test_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:  # 404 is expected until endpoint exists
                response.success()
                performance_tracker.record_response_time("/api/v1/process-data", response.elapsed.total_seconds())
            else:
                response.failure(f"Hebrew processing failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/process-data", f"status_{response.status_code}")


class IntensiveUser(BaseIDFUser):
    """Simulates intensive user behavior for stress testing"""
    
    weight = 1
    wait_time = between(0.5, 2)  # 0.5-2 seconds between requests
    
    @task(6)
    def rapid_fire_requests(self):
        """Make rapid requests to test system limits"""
        endpoints = ["/health", "/"]
        
        for endpoint in endpoints:
            with self.client.get(endpoint, catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                    performance_tracker.record_response_time(endpoint, response.elapsed.total_seconds())
                else:
                    response.failure(f"Rapid request failed with status {response.status_code}")
                    performance_tracker.record_error(endpoint, f"status_{response.status_code}")
    
    @task(3)
    def bulk_operations(self):
        """Simulate bulk data operations"""
        # Generate bulk test data
        bulk_data = [self.get_random_hebrew_data() for _ in range(10)]
        
        with self.client.post(
            "/api/v1/bulk-process",
            json={"data": bulk_data},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:  # 404 expected until endpoint exists
                response.success()
                performance_tracker.record_response_time("/api/v1/bulk-process", response.elapsed.total_seconds())
            else:
                response.failure(f"Bulk operation failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/bulk-process", f"status_{response.status_code}")
    
    @task(2)
    def concurrent_hebrew_processing(self):
        """Test concurrent Hebrew text processing"""
        test_data = self.get_random_hebrew_data()
        
        # Add some complexity to the Hebrew text
        test_data["description"] = test_data["description"] * 10  # Make it longer
        
        with self.client.post(
            "/api/v1/hebrew-intensive",
            json=test_data,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
                performance_tracker.record_response_time("/api/v1/hebrew-intensive", response.elapsed.total_seconds())
            else:
                response.failure(f"Hebrew intensive failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/hebrew-intensive", f"status_{response.status_code}")


class FileUploadUser(BaseIDFUser):
    """Simulates file upload scenarios"""
    
    weight = 1
    wait_time = between(5, 15)  # Longer wait times for file operations
    
    def create_test_file_data(self, size_kb: int = 100) -> bytes:
        """Create test file data"""
        # Create test Excel-like data
        test_content = "ID,Name,Description,Status\n"
        
        for i in range(size_kb):  # Approximate size
            hebrew_name = random.choice(HEBREW_TEST_DATA["test_names"])
            hebrew_desc = random.choice(HEBREW_TEST_DATA["descriptions"])
            status = random.choice(HEBREW_TEST_DATA["statuses"])
            test_content += f"{i},{hebrew_name},{hebrew_desc},{status}\n"
        
        return test_content.encode('utf-8')
    
    @task(3)
    def upload_small_file(self):
        """Upload small file"""
        file_data = self.create_test_file_data(10)  # 10KB
        
        with self.client.post(
            "/api/v1/upload",
            files={"file": ("test_small.csv", file_data, "text/csv")},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
                performance_tracker.record_response_time("/api/v1/upload", response.elapsed.total_seconds())
            else:
                response.failure(f"Small file upload failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/upload", f"status_{response.status_code}")
    
    @task(1)
    def upload_large_file(self):
        """Upload large file"""
        file_data = self.create_test_file_data(1000)  # 1MB
        
        with self.client.post(
            "/api/v1/upload",
            files={"file": ("test_large.csv", file_data, "text/csv")},
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
                performance_tracker.record_response_time("/api/v1/upload", response.elapsed.total_seconds())
            else:
                response.failure(f"Large file upload failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/upload", f"status_{response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def record_request_metrics(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Record custom request metrics"""
    if exception:
        error_counts["total"] += 1
        error_counts["by_endpoint"][name] = error_counts["by_endpoint"].get(name, 0) + 1
    
    response_times.append(response_time)


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")
    
    if isinstance(environment.runner, MasterRunner):
        logger.info("Running in distributed mode")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("Load test stopping...")
    
    # Print performance summary
    summary = performance_tracker.get_performance_summary()
    logger.info(f"Performance Summary: {json.dumps(summary, indent=2)}")
    
    # Print error summary
    if error_counts["total"] > 0:
        logger.warning(f"Total errors: {error_counts['total']}")
        logger.warning(f"Errors by endpoint: {json.dumps(error_counts['by_endpoint'], indent=2)}")
    
    # Print response time statistics
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        logger.info(f"Response time stats:")
        logger.info(f"  Average: {avg_response_time:.2f}ms")
        logger.info(f"  Maximum: {max_response_time:.2f}ms")
        logger.info(f"  Minimum: {min_response_time:.2f}ms")


# Custom load testing scenarios
class HebrewSpecificLoadTest(BaseIDFUser):
    """Specialized load test for Hebrew text processing"""
    
    weight = 1
    wait_time = between(1, 4)
    
    @task
    def hebrew_rtl_processing(self):
        """Test Hebrew RTL processing under load"""
        complex_hebrew = {
            "text": "זהו טקסט מורכב בעברית עם מספרים 123 ואותיות לטיניות ABC",
            "mixed_content": "Hello שלום World עולם!",
            "long_text": " ".join(HEBREW_TEST_DATA["descriptions"]) * 5
        }
        
        with self.client.post(
            "/api/v1/hebrew-rtl",
            json=complex_hebrew,
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
                performance_tracker.record_response_time("/api/v1/hebrew-rtl", response.elapsed.total_seconds())
            else:
                response.failure(f"Hebrew RTL failed with status {response.status_code}")
                performance_tracker.record_error("/api/v1/hebrew-rtl", f"status_{response.status_code}")


# Load testing configurations
class LightLoadTest(BaseIDFUser):
    """Light load test configuration"""
    weight = 1
    wait_time = between(3, 10)
    
    @task
    def light_operations(self):
        with self.client.get("/health") as response:
            pass


class HeavyLoadTest(BaseIDFUser):
    """Heavy load test configuration"""
    weight = 1
    wait_time = between(0.1, 1)
    
    @task
    def heavy_operations(self):
        endpoints = ["/health", "/"]
        for endpoint in endpoints:
            with self.client.get(endpoint) as response:
                pass


# Performance validation
def validate_performance_requirements():
    """Validate that performance meets requirements"""
    summary = performance_tracker.get_performance_summary()
    
    requirements = {
        "max_avg_response_time": 2.0,  # 2 seconds
        "max_error_rate": 0.05,        # 5%
        "min_throughput": 50           # 50 RPS
    }
    
    failures = []
    
    if summary.get("avg_response_time", 0) > requirements["max_avg_response_time"]:
        failures.append("Average response time exceeds requirement")
    
    if summary.get("error_rate", 0) > requirements["max_error_rate"]:
        failures.append("Error rate exceeds requirement")
    
    return len(failures) == 0, failures