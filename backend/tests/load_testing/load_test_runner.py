#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDF Testing Infrastructure - Load Test Runner
Automated load testing execution and reporting
"""

import subprocess
import json
import time
import os
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LoadTestConfig:
    """Load test configuration"""
    users: int = 50
    spawn_rate: int = 5
    duration: str = "5m"
    host: str = "http://localhost:8000"
    test_file: str = "locustfile.py"
    headless: bool = True
    csv_prefix: str = "load_test"
    html_report: str = "load_test_report.html"
    logfile: str = "load_test.log"


@dataclass
class PerformanceThresholds:
    """Performance thresholds for validation"""
    max_avg_response_time: float = 2.0  # seconds
    max_95th_percentile: float = 5.0    # seconds
    max_error_rate: float = 0.05        # 5%
    min_rps: float = 10.0              # requests per second


class LoadTestRunner:
    """Automated load test runner with performance validation"""
    
    def __init__(self, config: LoadTestConfig, thresholds: PerformanceThresholds):
        self.config = config
        self.thresholds = thresholds
        self.results = {}
        
    def check_target_availability(self) -> bool:
        """Check if target application is available"""
        try:
            response = requests.get(f"{self.config.host}/health", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Target not available: {e}")
            return False
    
    def run_load_test(self) -> bool:
        """Execute load test"""
        if not self.check_target_availability():
            logger.error("Target application is not available")
            return False
        
        logger.info(f"Starting load test with {self.config.users} users")
        logger.info(f"Target: {self.config.host}")
        logger.info(f"Duration: {self.config.duration}")
        
        # Build Locust command
        cmd = [
            "locust",
            "-f", self.config.test_file,
            "--host", self.config.host,
            "--users", str(self.config.users),
            "--spawn-rate", str(self.config.spawn_rate),
            "--run-time", self.config.duration,
            "--csv", self.config.csv_prefix,
            "--html", self.config.html_report,
            "--logfile", self.config.logfile
        ]
        
        if self.config.headless:
            cmd.append("--headless")
        
        try:
            # Run load test
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            end_time = time.time()
            
            logger.info(f"Load test completed in {end_time - start_time:.1f} seconds")
            
            if result.returncode == 0:
                logger.info("Load test executed successfully")
                self._parse_results()
                return True
            else:
                logger.error(f"Load test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Load test timed out")
            return False
        except Exception as e:
            logger.error(f"Error running load test: {e}")
            return False
    
    def _parse_results(self):
        """Parse load test results from CSV files"""
        try:
            # Parse stats file
            stats_file = f"{self.config.csv_prefix}_stats.csv"
            if os.path.exists(stats_file):
                self.results['stats'] = self._parse_csv_file(stats_file)
            
            # Parse failures file
            failures_file = f"{self.config.csv_prefix}_failures.csv"
            if os.path.exists(failures_file):
                self.results['failures'] = self._parse_csv_file(failures_file)
            
            # Parse stats history
            history_file = f"{self.config.csv_prefix}_stats_history.csv"
            if os.path.exists(history_file):
                self.results['history'] = self._parse_csv_file(history_file)
                
        except Exception as e:
            logger.error(f"Error parsing results: {e}")
    
    def _parse_csv_file(self, filename: str) -> List[Dict]:
        """Parse CSV file into list of dictionaries"""
        import csv
        
        data = []
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(row)
        
        return data
    
    def validate_performance(self) -> bool:
        """Validate performance against thresholds"""
        if not self.results.get('stats'):
            logger.error("No stats available for validation")
            return False
        
        # Get aggregated stats (usually the last row with "Aggregated" name)
        aggregated_stats = None
        for row in self.results['stats']:
            if row.get('Name') == 'Aggregated':
                aggregated_stats = row
                break
        
        if not aggregated_stats:
            logger.error("No aggregated stats found")
            return False
        
        validation_results = []
        
        try:
            # Check average response time
            avg_response_time = float(aggregated_stats.get('Average Response Time', 0)) / 1000  # Convert to seconds
            if avg_response_time > self.thresholds.max_avg_response_time:
                validation_results.append(
                    f"Average response time {avg_response_time:.2f}s exceeds threshold {self.thresholds.max_avg_response_time}s"
                )
            
            # Check 95th percentile
            percentile_95 = float(aggregated_stats.get('95%', 0)) / 1000
            if percentile_95 > self.thresholds.max_95th_percentile:
                validation_results.append(
                    f"95th percentile {percentile_95:.2f}s exceeds threshold {self.thresholds.max_95th_percentile}s"
                )
            
            # Check error rate
            failure_count = int(aggregated_stats.get('Failure Count', 0))
            request_count = int(aggregated_stats.get('Request Count', 0))
            error_rate = failure_count / request_count if request_count > 0 else 0
            
            if error_rate > self.thresholds.max_error_rate:
                validation_results.append(
                    f"Error rate {error_rate:.2%} exceeds threshold {self.thresholds.max_error_rate:.2%}"
                )
            
            # Check RPS
            rps = float(aggregated_stats.get('Requests/s', 0))
            if rps < self.thresholds.min_rps:
                validation_results.append(
                    f"RPS {rps:.1f} below threshold {self.thresholds.min_rps}"
                )
            
        except (ValueError, KeyError) as e:
            logger.error(f"Error validating performance: {e}")
            return False
        
        if validation_results:
            logger.error("Performance validation failed:")
            for result in validation_results:
                logger.error(f"  - {result}")
            return False
        else:
            logger.info("Performance validation passed")
            return True
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        if not self.results.get('stats'):
            return {"error": "No performance data available"}
        
        aggregated_stats = None
        for row in self.results['stats']:
            if row.get('Name') == 'Aggregated':
                aggregated_stats = row
                break
        
        if not aggregated_stats:
            return {"error": "No aggregated stats found"}
        
        try:
            report = {
                "test_config": {
                    "users": self.config.users,
                    "spawn_rate": self.config.spawn_rate,
                    "duration": self.config.duration,
                    "host": self.config.host
                },
                "performance_metrics": {
                    "total_requests": int(aggregated_stats.get('Request Count', 0)),
                    "failure_count": int(aggregated_stats.get('Failure Count', 0)),
                    "average_response_time_ms": float(aggregated_stats.get('Average Response Time', 0)),
                    "min_response_time_ms": float(aggregated_stats.get('Min Response Time', 0)),
                    "max_response_time_ms": float(aggregated_stats.get('Max Response Time', 0)),
                    "median_response_time_ms": float(aggregated_stats.get('Median Response Time', 0)),
                    "percentile_95_ms": float(aggregated_stats.get('95%', 0)),
                    "percentile_99_ms": float(aggregated_stats.get('99%', 0)),
                    "requests_per_second": float(aggregated_stats.get('Requests/s', 0)),
                    "failures_per_second": float(aggregated_stats.get('Failures/s', 0))
                },
                "calculated_metrics": {
                    "error_rate": (
                        int(aggregated_stats.get('Failure Count', 0)) / 
                        int(aggregated_stats.get('Request Count', 1))
                    ),
                    "success_rate": 1 - (
                        int(aggregated_stats.get('Failure Count', 0)) / 
                        int(aggregated_stats.get('Request Count', 1))
                    )
                },
                "thresholds": {
                    "max_avg_response_time_s": self.thresholds.max_avg_response_time,
                    "max_95th_percentile_s": self.thresholds.max_95th_percentile,
                    "max_error_rate": self.thresholds.max_error_rate,
                    "min_rps": self.thresholds.min_rps
                },
                "validation_passed": self.validate_performance(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add endpoint-specific metrics
            endpoint_metrics = {}
            for row in self.results['stats']:
                if row.get('Name') != 'Aggregated' and row.get('Name'):
                    endpoint_metrics[row['Name']] = {
                        "requests": int(row.get('Request Count', 0)),
                        "failures": int(row.get('Failure Count', 0)),
                        "avg_response_time_ms": float(row.get('Average Response Time', 0)),
                        "rps": float(row.get('Requests/s', 0))
                    }
            
            report["endpoint_metrics"] = endpoint_metrics
            
            # Add failure details if any
            if self.results.get('failures'):
                report["failure_details"] = self.results['failures']
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}
    
    def cleanup_files(self):
        """Clean up generated files"""
        files_to_cleanup = [
            f"{self.config.csv_prefix}_stats.csv",
            f"{self.config.csv_prefix}_failures.csv",
            f"{self.config.csv_prefix}_stats_history.csv",
            self.config.html_report,
            self.config.logfile
        ]
        
        for file in files_to_cleanup:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    logger.debug(f"Removed {file}")
                except Exception as e:
                    logger.warning(f"Could not remove {file}: {e}")


def run_load_test_suite():
    """Run comprehensive load test suite"""
    test_configs = [
        {
            "name": "Light Load Test",
            "config": LoadTestConfig(users=10, spawn_rate=2, duration="2m"),
            "thresholds": PerformanceThresholds(max_avg_response_time=1.0, min_rps=5.0)
        },
        {
            "name": "Normal Load Test",
            "config": LoadTestConfig(users=50, spawn_rate=5, duration="5m"),
            "thresholds": PerformanceThresholds(max_avg_response_time=2.0, min_rps=20.0)
        },
        {
            "name": "Heavy Load Test",
            "config": LoadTestConfig(users=100, spawn_rate=10, duration="3m"),
            "thresholds": PerformanceThresholds(max_avg_response_time=5.0, max_error_rate=0.1)
        }
    ]
    
    all_results = []
    
    for test in test_configs:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running {test['name']}")
        logger.info(f"{'='*50}")
        
        runner = LoadTestRunner(test['config'], test['thresholds'])
        
        if runner.run_load_test():
            report = runner.generate_performance_report()
            report['test_name'] = test['name']
            all_results.append(report)
            
            # Save individual report
            report_file = f"load_test_report_{test['name'].lower().replace(' ', '_')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Report saved to {report_file}")
        else:
            logger.error(f"{test['name']} failed")
        
        # Cleanup
        runner.cleanup_files()
        
        # Wait between tests
        time.sleep(30)
    
    # Generate summary report
    summary_report = {
        "suite_execution_time": datetime.utcnow().isoformat(),
        "total_tests": len(test_configs),
        "passed_tests": len([r for r in all_results if r.get('validation_passed', False)]),
        "failed_tests": len([r for r in all_results if not r.get('validation_passed', True)]),
        "individual_results": all_results
    }
    
    with open("load_test_suite_summary.json", 'w') as f:
        json.dump(summary_report, f, indent=2)
    
    logger.info(f"\nLoad test suite completed. Summary saved to load_test_suite_summary.json")
    logger.info(f"Passed: {summary_report['passed_tests']}/{summary_report['total_tests']}")
    
    return summary_report


if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description="Run load tests for IDF Testing Infrastructure")
    parser.add_argument("--host", default="http://localhost:8000", help="Target host")
    parser.add_argument("--users", type=int, default=50, help="Number of users")
    parser.add_argument("--spawn-rate", type=int, default=5, help="Spawn rate")
    parser.add_argument("--duration", default="5m", help="Test duration")
    parser.add_argument("--suite", action="store_true", help="Run full test suite")
    
    args = parser.parse_args()
    
    if args.suite:
        run_load_test_suite()
    else:
        config = LoadTestConfig(
            users=args.users,
            spawn_rate=args.spawn_rate,
            duration=args.duration,
            host=args.host
        )
        thresholds = PerformanceThresholds()
        
        runner = LoadTestRunner(config, thresholds)
        
        if runner.run_load_test():
            report = runner.generate_performance_report()
            
            with open("load_test_report.json", 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info("Load test completed. Report saved to load_test_report.json")
            
            if report.get('validation_passed'):
                logger.info("Performance validation PASSED")
                sys.exit(0)
            else:
                logger.error("Performance validation FAILED")
                sys.exit(1)
        else:
            logger.error("Load test failed")
            sys.exit(1)