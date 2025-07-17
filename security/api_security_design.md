# API Security Design

## 1. API Security Architecture

### 1.1 Security Layers
```
Client → WAF → API Gateway → Rate Limiter → Auth Service → Application → Database
   ↓       ↓         ↓           ↓            ↓            ↓            ↓
SSL/TLS  Filtering  Routing   Throttling   JWT/OAuth2   Validation   Encryption
```

### 1.2 API Security Components
```python
class APISecurityFramework:
    def __init__(self):
        self.components = {
            'input_validation': InputValidator(),
            'rate_limiter': RateLimiter(),
            'authentication': AuthenticationService(),
            'authorization': AuthorizationService(),
            'output_sanitization': OutputSanitizer(),
            'logging': SecurityLogger(),
            'monitoring': ThreatMonitor()
        }
    
    def secure_api_request(self, request):
        # 1. Input validation
        validated_request = self.components['input_validation'].validate(request)
        
        # 2. Rate limiting
        self.components['rate_limiter'].check_limits(request.client_id)
        
        # 3. Authentication
        auth_context = self.components['authentication'].authenticate(request)
        
        # 4. Authorization
        self.components['authorization'].authorize(auth_context, request.endpoint)
        
        # 5. Process request
        response = self.process_request(validated_request)
        
        # 6. Output sanitization
        sanitized_response = self.components['output_sanitization'].sanitize(response)
        
        # 7. Security logging
        self.components['logging'].log_api_access(request, response, auth_context)
        
        return sanitized_response
```

## 2. Input Validation & Sanitization

### 2.1 Comprehensive Input Validation
```python
class InputValidator:
    def __init__(self):
        self.validation_rules = {
            'string': self.validate_string,
            'integer': self.validate_integer,
            'email': self.validate_email,
            'url': self.validate_url,
            'uuid': self.validate_uuid,
            'json': self.validate_json,
            'file': self.validate_file
        }
        
        self.max_payload_size = 10 * 1024 * 1024  # 10MB
        self.max_string_length = 10000
        self.allowed_content_types = [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data'
        ]
    
    def validate_request(self, request):
        # Size validation
        if len(request.body) > self.max_payload_size:
            raise PayloadTooLargeError("Request payload exceeds maximum size")
        
        # Content-Type validation
        if request.content_type not in self.allowed_content_types:
            raise InvalidContentTypeError("Unsupported content type")
        
        # Schema validation
        self.validate_schema(request.data, request.endpoint_schema)
        
        # Injection attack prevention
        self.check_for_injections(request.data)
        
        return request
    
    def validate_string(self, value, field_config):
        if not isinstance(value, str):
            raise ValidationError(f"Field must be string: {field_config.name}")
        
        # Length validation
        if len(value) > field_config.max_length:
            raise ValidationError(f"String too long: {field_config.name}")
        
        # Pattern validation
        if field_config.pattern and not re.match(field_config.pattern, value):
            raise ValidationError(f"Pattern mismatch: {field_config.name}")
        
        # Dangerous character detection
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        if any(char in value for char in dangerous_chars):
            value = self.sanitize_string(value)
        
        return value
    
    def check_for_injections(self, data):
        """Check for common injection attack patterns"""
        injection_patterns = [
            # SQL Injection
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+[\"']\w+[\"']\s*=\s*[\"']\w+[\"'])",
            
            # NoSQL Injection
            r"(\$where|\$regex|\$ne|\$gt|\$lt)",
            
            # XSS
            r"(<script|javascript:|onerror=|onload=)",
            
            # Command Injection
            r"(;|\||\&|\$\(|\`)",
            
            # LDAP Injection
            r"(\(\||\(\&|\(\!)"
        ]
        
        data_str = str(data)
        for pattern in injection_patterns:
            if re.search(pattern, data_str, re.IGNORECASE):
                raise InjectionAttackDetectedError(f"Potential injection detected: {pattern}")
```

### 2.2 File Upload Security
```python
class FileUploadValidator:
    def __init__(self):
        self.allowed_extensions = {
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'documents': ['.pdf', '.doc', '.docx', '.txt', '.csv'],
            'archives': ['.zip', '.tar', '.gz']
        }
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.virus_scanner = VirusScanner()
    
    def validate_file_upload(self, file, file_type_category):
        # File size validation
        if file.size > self.max_file_size:
            raise FileTooLargeError("File exceeds maximum size limit")
        
        # Extension validation
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in self.allowed_extensions[file_type_category]:
            raise InvalidFileTypeError("File type not allowed")
        
        # MIME type validation
        detected_mime = magic.from_buffer(file.read(1024), mime=True)
        expected_mimes = self.get_expected_mimes(file_ext)
        if detected_mime not in expected_mimes:
            raise MimeTypeMismatchError("File content doesn't match extension")
        
        # Virus scanning
        virus_scan_result = self.virus_scanner.scan(file)
        if virus_scan_result.infected:
            raise VirusDetectedError("Malicious file detected")
        
        # File content validation
        self.validate_file_content(file, file_type_category)
        
        return file
    
    def validate_file_content(self, file, category):
        """Validate file content based on category"""
        if category == 'images':
            self.validate_image_file(file)
        elif category == 'documents':
            self.validate_document_file(file)
    
    def validate_image_file(self, file):
        try:
            with Image.open(file) as img:
                # Check for embedded scripts or suspicious metadata
                if self.has_suspicious_metadata(img):
                    raise SuspiciousFileError("Image contains suspicious metadata")
                
                # Validate image dimensions
                if img.width > 10000 or img.height > 10000:
                    raise InvalidImageError("Image dimensions too large")
        except Exception as e:
            raise InvalidImageError(f"Invalid image file: {str(e)}")
```

## 3. Rate Limiting & Throttling

### 3.1 Advanced Rate Limiting
```python
class AdvancedRateLimiter:
    def __init__(self):
        self.algorithms = {
            'token_bucket': TokenBucket(),
            'sliding_window': SlidingWindow(),
            'fixed_window': FixedWindow(),
            'sliding_window_counter': SlidingWindowCounter()
        }
        
        self.rate_limit_configs = {
            'public_api': {
                'requests_per_minute': 100,
                'requests_per_hour': 5000,
                'burst_allowance': 20,
                'algorithm': 'sliding_window'
            },
            'authenticated_api': {
                'requests_per_minute': 1000,
                'requests_per_hour': 50000,
                'burst_allowance': 100,
                'algorithm': 'token_bucket'
            },
            'premium_api': {
                'requests_per_minute': 10000,
                'requests_per_hour': 500000,
                'burst_allowance': 1000,
                'algorithm': 'sliding_window_counter'
            }
        }
    
    def check_rate_limit(self, client_id, endpoint, user_tier='public_api'):
        config = self.rate_limit_configs[user_tier]
        algorithm = self.algorithms[config['algorithm']]
        
        # Check multiple time windows
        minute_limit = algorithm.is_allowed(
            client_id, 
            config['requests_per_minute'], 
            window_size=60
        )
        
        hour_limit = algorithm.is_allowed(
            client_id, 
            config['requests_per_hour'], 
            window_size=3600
        )
        
        if not minute_limit:
            raise RateLimitExceededError("Minute rate limit exceeded", retry_after=60)
        
        if not hour_limit:
            raise RateLimitExceededError("Hour rate limit exceeded", retry_after=3600)
        
        # Update rate limit headers
        return {
            'X-RateLimit-Limit': config['requests_per_minute'],
            'X-RateLimit-Remaining': algorithm.get_remaining(client_id),
            'X-RateLimit-Reset': algorithm.get_reset_time(client_id)
        }
```

### 3.2 Adaptive Rate Limiting
```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.base_limits = {'requests_per_minute': 1000}
        self.threat_detector = ThreatDetector()
        self.reputation_engine = ReputationEngine()
    
    def calculate_dynamic_limit(self, client_id, endpoint):
        base_limit = self.base_limits['requests_per_minute']
        
        # Reputation-based adjustment
        reputation_score = self.reputation_engine.get_score(client_id)
        reputation_multiplier = self.get_reputation_multiplier(reputation_score)
        
        # Threat level adjustment
        threat_level = self.threat_detector.get_current_threat_level()
        threat_multiplier = self.get_threat_multiplier(threat_level)
        
        # Endpoint-specific adjustment
        endpoint_multiplier = self.get_endpoint_multiplier(endpoint)
        
        # Calculate final limit
        dynamic_limit = int(
            base_limit * 
            reputation_multiplier * 
            threat_multiplier * 
            endpoint_multiplier
        )
        
        return max(dynamic_limit, 10)  # Minimum 10 requests per minute
    
    def get_reputation_multiplier(self, reputation_score):
        """Convert reputation score (0-100) to rate limit multiplier"""
        if reputation_score >= 90:
            return 2.0  # High reputation gets 2x limit
        elif reputation_score >= 70:
            return 1.5  # Good reputation gets 1.5x limit
        elif reputation_score >= 50:
            return 1.0  # Average reputation gets base limit
        elif reputation_score >= 30:
            return 0.5  # Poor reputation gets 0.5x limit
        else:
            return 0.1  # Very poor reputation gets 0.1x limit
```

## 4. API Security Headers

### 4.1 Security Headers Configuration
```python
class APISecurityHeaders:
    def __init__(self):
        self.security_headers = {
            # Basic security headers
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            
            # HTTPS enforcement
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
            
            # Content Security Policy
            'Content-Security-Policy': self.build_csp_policy(),
            
            # Feature Policy
            'Permissions-Policy': (
                'geolocation=(), microphone=(), camera=(), '
                'payment=(), usb=(), magnetometer=(), accelerometer=(), '
                'gyroscope=(), speaker=(), vibrate=(), fullscreen=()'
            ),
            
            # Custom security headers
            'X-API-Version': '1.0',
            'X-Rate-Limit-Policy': 'strict',
            'X-Security-Policy': 'enforced'
        }
    
    def build_csp_policy(self):
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.trusted.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' https://api.company.com; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
    
    def apply_headers(self, response, endpoint_config=None):
        headers = self.security_headers.copy()
        
        # Endpoint-specific header customization
        if endpoint_config:
            if endpoint_config.get('cors_enabled'):
                headers.update(self.get_cors_headers(endpoint_config))
            
            if endpoint_config.get('cache_control'):
                headers['Cache-Control'] = endpoint_config['cache_control']
        
        # Apply all headers to response
        for header, value in headers.items():
            response.headers[header] = value
        
        return response
```

### 4.2 CORS Security Configuration
```python
class CORSSecurityManager:
    def __init__(self):
        self.cors_policies = {
            'strict': {
                'allowed_origins': ['https://app.company.com'],
                'allowed_methods': ['GET', 'POST'],
                'allowed_headers': ['Authorization', 'Content-Type'],
                'expose_headers': ['X-RateLimit-Remaining'],
                'allow_credentials': True,
                'max_age': 600
            },
            'moderate': {
                'allowed_origins': [
                    'https://app.company.com',
                    'https://admin.company.com'
                ],
                'allowed_methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'allowed_headers': [
                    'Authorization', 'Content-Type', 
                    'X-Requested-With', 'X-CSRF-Token'
                ],
                'expose_headers': [
                    'X-RateLimit-Remaining', 
                    'X-RateLimit-Reset'
                ],
                'allow_credentials': True,
                'max_age': 3600
            }
        }
    
    def validate_cors_request(self, request, policy_name='strict'):
        policy = self.cors_policies[policy_name]
        origin = request.headers.get('Origin')
        
        # Validate origin
        if origin not in policy['allowed_origins']:
            raise CORSViolationError(f"Origin not allowed: {origin}")
        
        # Validate method for preflight requests
        if request.method == 'OPTIONS':
            requested_method = request.headers.get('Access-Control-Request-Method')
            if requested_method not in policy['allowed_methods']:
                raise CORSViolationError(f"Method not allowed: {requested_method}")
        
        return policy
```

## 5. API Versioning Security

### 5.1 Version-Based Security Policies
```python
class APIVersionSecurity:
    def __init__(self):
        self.version_policies = {
            'v1': {
                'deprecated': True,
                'sunset_date': '2024-12-31',
                'security_level': 'legacy',
                'rate_limit_multiplier': 0.5,
                'required_auth_level': 'high'
            },
            'v2': {
                'deprecated': False,
                'security_level': 'standard',
                'rate_limit_multiplier': 1.0,
                'required_auth_level': 'medium'
            },
            'v3': {
                'deprecated': False,
                'security_level': 'enhanced',
                'rate_limit_multiplier': 1.5,
                'required_auth_level': 'low',
                'features': ['enhanced_encryption', 'advanced_monitoring']
            }
        }
    
    def validate_api_version(self, request):
        version = self.extract_version(request)
        policy = self.version_policies.get(version)
        
        if not policy:
            raise UnsupportedVersionError(f"API version {version} not supported")
        
        if policy.get('deprecated') and self.is_sunset_date_passed(policy):
            raise DeprecatedVersionError(f"API version {version} is no longer supported")
        
        # Apply version-specific security requirements
        self.apply_version_security(request, policy)
        
        return version, policy
    
    def apply_version_security(self, request, policy):
        # Enhanced authentication for deprecated versions
        if policy.get('deprecated'):
            self.require_enhanced_auth(request)
        
        # Version-specific rate limiting
        rate_multiplier = policy.get('rate_limit_multiplier', 1.0)
        request.rate_limit_multiplier = rate_multiplier
        
        # Additional security features for newer versions
        if 'enhanced_encryption' in policy.get('features', []):
            request.require_enhanced_encryption = True
```

## 6. API Monitoring & Threat Detection

### 6.1 Real-time Threat Detection
```python
class APIThreatDetector:
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.signature_scanner = SignatureScanner()
        self.ml_classifier = MLThreatClassifier()
        
        self.threat_patterns = {
            'brute_force': {
                'failed_attempts_threshold': 10,
                'time_window': 300,  # 5 minutes
                'action': 'block_ip'
            },
            'credential_stuffing': {
                'unique_usernames_threshold': 100,
                'time_window': 3600,  # 1 hour
                'action': 'captcha_challenge'
            },
            'api_abuse': {
                'error_rate_threshold': 0.5,
                'request_count_threshold': 1000,
                'time_window': 600,  # 10 minutes
                'action': 'rate_limit'
            }
        }
    
    def analyze_request(self, request, context):
        threats_detected = []
        
        # Signature-based detection
        signature_threats = self.signature_scanner.scan(request)
        threats_detected.extend(signature_threats)
        
        # Anomaly detection
        if self.anomaly_detector.is_anomalous(request, context):
            threats_detected.append({
                'type': 'anomaly',
                'severity': 'medium',
                'description': 'Unusual request pattern detected'
            })
        
        # ML-based classification
        ml_prediction = self.ml_classifier.predict_threat(request)
        if ml_prediction.probability > 0.8:
            threats_detected.append({
                'type': 'ml_prediction',
                'severity': ml_prediction.severity,
                'description': ml_prediction.description,
                'confidence': ml_prediction.probability
            })
        
        # Pattern-based detection
        pattern_threats = self.detect_attack_patterns(request, context)
        threats_detected.extend(pattern_threats)
        
        return threats_detected
    
    def detect_attack_patterns(self, request, context):
        detected_patterns = []
        client_id = context.client_id
        
        for pattern_name, pattern_config in self.threat_patterns.items():
            if self.matches_attack_pattern(client_id, pattern_config):
                detected_patterns.append({
                    'type': pattern_name,
                    'severity': 'high',
                    'action': pattern_config['action'],
                    'description': f'{pattern_name} attack pattern detected'
                })
        
        return detected_patterns
```

### 6.2 Automated Response System
```python
class AutomatedResponseSystem:
    def __init__(self):
        self.response_actions = {
            'block_ip': self.block_ip_address,
            'rate_limit': self.apply_temporary_rate_limit,
            'captcha_challenge': self.require_captcha,
            'quarantine': self.quarantine_user,
            'alert_admin': self.send_admin_alert
        }
    
    def respond_to_threat(self, threat, request_context):
        action = threat.get('action', 'alert_admin')
        severity = threat.get('severity', 'medium')
        
        # Execute primary response action
        response = self.response_actions[action](threat, request_context)
        
        # Execute severity-based additional actions
        if severity == 'critical':
            self.send_admin_alert(threat, request_context)
            self.log_security_incident(threat, request_context)
        elif severity == 'high':
            self.log_security_event(threat, request_context)
        
        # Update threat intelligence
        self.update_threat_intelligence(threat, request_context)
        
        return response
    
    def block_ip_address(self, threat, context):
        ip_address = context.ip_address
        
        # Add to IP blacklist
        self.ip_blacklist.add(ip_address, {
            'reason': threat['description'],
            'duration': self.calculate_block_duration(threat),
            'timestamp': datetime.utcnow()
        })
        
        # Update firewall rules
        self.firewall.add_block_rule(ip_address)
        
        return {
            'action': 'ip_blocked',
            'ip_address': ip_address,
            'duration': self.calculate_block_duration(threat)
        }
```

## 7. API Documentation Security

### 7.1 Secure API Documentation
```python
class SecureAPIDocumentation:
    def __init__(self):
        self.documentation_levels = {
            'public': {
                'show_examples': True,
                'show_error_codes': False,
                'show_internal_endpoints': False,
                'mask_sensitive_data': True
            },
            'partner': {
                'show_examples': True,
                'show_error_codes': True,
                'show_internal_endpoints': False,
                'mask_sensitive_data': True
            },
            'internal': {
                'show_examples': True,
                'show_error_codes': True,
                'show_internal_endpoints': True,
                'mask_sensitive_data': False
            }
        }
    
    def generate_documentation(self, endpoints, user_level='public'):
        config = self.documentation_levels[user_level]
        filtered_endpoints = []
        
        for endpoint in endpoints:
            if not config['show_internal_endpoints'] and endpoint.is_internal:
                continue
            
            # Filter sensitive information
            doc_endpoint = self.filter_endpoint_doc(endpoint, config)
            filtered_endpoints.append(doc_endpoint)
        
        return self.render_documentation(filtered_endpoints, config)
    
    def filter_endpoint_doc(self, endpoint, config):
        filtered_endpoint = endpoint.copy()
        
        # Remove sensitive examples
        if config['mask_sensitive_data']:
            filtered_endpoint.examples = self.mask_sensitive_examples(endpoint.examples)
        
        # Filter error information
        if not config['show_error_codes']:
            filtered_endpoint.error_responses = self.filter_error_responses(
                endpoint.error_responses
            )
        
        return filtered_endpoint
```

This comprehensive API security design provides multiple layers of protection against common and advanced threats while maintaining usability and performance for legitimate users.