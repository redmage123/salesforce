#!/usr/bin/env python3
"""
GDPR Compliance Evaluator

Evaluates web implementations for GDPR (General Data Protection Regulation) compliance.
Uses static analysis and pattern matching to detect privacy and data protection issues.

For production use, integrate with:
- OneTrust
- TrustArc
- Osano
- Cookie consent libraries
"""

import re
import json
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class GDPRIssue:
    """Represents a single GDPR compliance issue"""
    article: str  # GDPR article violated (e.g., "Article 7" for consent)
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "consent", "data_minimization", "right_to_erasure", etc.
    description: str  # Human-readable description
    suggestion: str  # How to fix
    gdpr_principle: str  # GDPR principle name


class GDPREvaluator:
    """
    GDPR Compliance Evaluator

    Checks for common GDPR violations through static analysis.
    For production, should be supplemented with manual privacy audits.
    """

    def __init__(self):
        self.issues: List[GDPRIssue] = []

    def evaluate_directory(self, implementation_dir: str) -> Dict:
        """
        Evaluate implementation directory for GDPR compliance

        Args:
            implementation_dir: Path to implementation directory

        Returns:
            Dict with evaluation results
        """
        self.issues = []
        impl_path = Path(implementation_dir)

        if not impl_path.exists():
            return self._create_result(skipped=True, reason="Directory not found")

        # Find all relevant files
        code_files = list(impl_path.rglob("*.js")) + \
                    list(impl_path.rglob("*.jsx")) + \
                    list(impl_path.rglob("*.ts")) + \
                    list(impl_path.rglob("*.tsx")) + \
                    list(impl_path.rglob("*.py")) + \
                    list(impl_path.rglob("*.html"))

        if not code_files:
            return self._create_result(skipped=True, reason="No code files found")

        # Evaluate each file
        for file_path in code_files:
            self._evaluate_file(file_path)

        return self._create_result()

    def _evaluate_file(self, file_path: Path):
        """Evaluate a single file for GDPR compliance"""
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return  # Skip files that can't be read

        # Run all GDPR checks
        self._check_cookie_consent(content, str(file_path))
        self._check_data_collection(content, str(file_path))
        self._check_data_minimization(content, str(file_path))
        self._check_right_to_erasure(content, str(file_path))
        self._check_data_portability(content, str(file_path))
        self._check_privacy_by_design(content, str(file_path))
        self._check_third_party_tracking(content, str(file_path))
        self._check_personal_data_storage(content, str(file_path))

    def _check_cookie_consent(self, content: str, file_path: str):
        """
        GDPR Article 7 - Conditions for consent
        Check for cookie consent implementation
        """
        # Look for cookie usage without consent mechanism
        cookie_patterns = [
            r'document\.cookie\s*=',
            r'localStorage\.setItem',
            r'sessionStorage\.setItem',
            r'Cookies\.set'
        ]

        has_cookie_usage = any(re.search(pattern, content) for pattern in cookie_patterns)

        # Look for consent mechanisms
        consent_patterns = [
            r'cookie.*consent',
            r'acceptCookies',
            r'cookieBanner',
            r'GDPR.*consent'
        ]

        has_consent_mechanism = any(re.search(pattern, content, re.IGNORECASE) for pattern in consent_patterns)

        if has_cookie_usage and not has_consent_mechanism:
            self.issues.append(GDPRIssue(
                article="Article 7",
                severity="critical",
                category="consent",
                description="Cookie usage detected without consent mechanism",
                suggestion="Implement cookie consent banner before storing cookies",
                gdpr_principle="Lawful basis for processing"
            ))

    def _check_data_collection(self, content: str, file_path: str):
        """
        GDPR Article 13 - Information to be provided when data is collected
        Check for privacy policy links and data collection notices
        """
        # Look for forms collecting personal data
        form_fields = [
            r'<input[^>]*type=["\']email',
            r'<input[^>]*name=["\']email',
            r'<input[^>]*type=["\']tel',
            r'<input[^>]*name=["\']phone',
            r'<input[^>]*name=["\']ssn',
            r'<input[^>]*name=["\']address'
        ]

        has_personal_data_form = any(re.search(pattern, content, re.IGNORECASE) for pattern in form_fields)

        # Look for privacy notice
        privacy_patterns = [
            r'privacy.*policy',
            r'data.*protection',
            r'terms.*service'
        ]

        has_privacy_notice = any(re.search(pattern, content, re.IGNORECASE) for pattern in privacy_patterns)

        if has_personal_data_form and not has_privacy_notice:
            self.issues.append(GDPRIssue(
                article="Article 13",
                severity="high",
                category="transparency",
                description="Personal data collection without privacy notice",
                suggestion="Add link to privacy policy near data collection forms",
                gdpr_principle="Transparency and information"
            ))

    def _check_data_minimization(self, content: str, file_path: str):
        """
        GDPR Article 5(1)(c) - Data minimization
        Check for excessive data collection
        """
        # Look for collection of sensitive data that might not be necessary
        sensitive_fields = [
            (r'ssn|social.*security', 'Social Security Number'),
            (r'birthdate|date.*birth', 'Date of Birth'),
            (r'race|ethnicity', 'Race/Ethnicity'),
            (r'religion|religious', 'Religious beliefs'),
            (r'sexual.*orientation', 'Sexual orientation'),
            (r'political.*views', 'Political views')
        ]

        for pattern, data_type in sensitive_fields:
            if re.search(pattern, content, re.IGNORECASE):
                self.issues.append(GDPRIssue(
                    article="Article 5(1)(c)",
                    severity="high",
                    category="data_minimization",
                    description=f"Collection of {data_type} detected - may violate data minimization",
                    suggestion=f"Ensure {data_type} collection is necessary and justified",
                    gdpr_principle="Data minimization"
                ))

    def _check_right_to_erasure(self, content: str, file_path: str):
        """
        GDPR Article 17 - Right to erasure ('right to be forgotten')
        Check for data deletion functionality
        """
        # Look for user data storage
        user_data_patterns = [
            r'(users?|accounts?|profiles?)\.save',
            r'(users?|accounts?|profiles?)\.create',
            r'INSERT\s+INTO\s+(users?|accounts?|profiles?)'
        ]

        has_user_data_storage = any(re.search(pattern, content, re.IGNORECASE) for pattern in user_data_patterns)

        # Look for deletion functionality
        deletion_patterns = [
            r'(delete|remove|erase).*account',
            r'DELETE\s+FROM\s+(users?|accounts?)',
            r'\.(delete|destroy)\(',
            r'right.*to.*erasure'
        ]

        has_deletion_feature = any(re.search(pattern, content, re.IGNORECASE) for pattern in deletion_patterns)

        if has_user_data_storage and not has_deletion_feature:
            # Only warn if this looks like a backend/API file
            if '.py' in file_path or 'api' in file_path.lower() or 'server' in file_path.lower():
                self.issues.append(GDPRIssue(
                    article="Article 17",
                    severity="high",
                    category="right_to_erasure",
                    description="User data storage without deletion functionality",
                    suggestion="Implement user account deletion feature (right to be forgotten)",
                    gdpr_principle="Right to erasure"
                ))

    def _check_data_portability(self, content: str, file_path: str):
        """
        GDPR Article 20 - Right to data portability
        Check for data export functionality
        """
        # Look for user data storage
        has_user_data = bool(re.search(r'(users?|accounts?|profiles?)', content, re.IGNORECASE))

        # Look for export functionality
        export_patterns = [
            r'export.*data',
            r'download.*data',
            r'data.*portability',
            r'\.csv|\.json.*export'
        ]

        has_export_feature = any(re.search(pattern, content, re.IGNORECASE) for pattern in export_patterns)

        if has_user_data and not has_export_feature:
            # Only check in backend/API files
            if '.py' in file_path or 'api' in file_path.lower() or 'server' in file_path.lower():
                self.issues.append(GDPRIssue(
                    article="Article 20",
                    severity="medium",
                    category="data_portability",
                    description="User data storage without export functionality",
                    suggestion="Implement data export feature (right to data portability)",
                    gdpr_principle="Right to data portability"
                ))

    def _check_privacy_by_design(self, content: str, file_path: str):
        """
        GDPR Article 25 - Data protection by design and by default
        Check for privacy-first patterns
        """
        # Look for hardcoded secrets or API keys
        secret_patterns = [
            (r'api[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9]{20,}', 'API key'),
            (r'password\s*[=:]\s*["\'][^"\']+["\']', 'Password'),
            (r'secret\s*[=:]\s*["\'][^"\']+["\']', 'Secret'),
            (r'token\s*[=:]\s*["\'][a-zA-Z0-9]{20,}', 'Token')
        ]

        for pattern, secret_type in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.issues.append(GDPRIssue(
                    article="Article 25",
                    severity="critical",
                    category="privacy_by_design",
                    description=f"Hardcoded {secret_type} detected - security risk",
                    suggestion=f"Use environment variables or secure vault for {secret_type}",
                    gdpr_principle="Data protection by design"
                ))

    def _check_third_party_tracking(self, content: str, file_path: str):
        """
        GDPR Article 7 - Conditions for consent
        Check for third-party tracking without consent
        """
        # Look for common tracking services
        tracking_services = [
            (r'google-analytics|ga\(|gtag\(', 'Google Analytics'),
            (r'facebook.*pixel|fbq\(', 'Facebook Pixel'),
            (r'mixpanel', 'Mixpanel'),
            (r'hotjar', 'Hotjar'),
            (r'segment\.', 'Segment')
        ]

        for pattern, service in tracking_services:
            if re.search(pattern, content, re.IGNORECASE):
                # Check if there's consent handling
                consent_check = r'(consent|gdpr|cookie.*accept)'
                if not re.search(consent_check, content, re.IGNORECASE):
                    self.issues.append(GDPRIssue(
                        article="Article 7",
                        severity="critical",
                        category="consent",
                        description=f"{service} tracking detected without consent check",
                        suggestion=f"Only load {service} after user consent",
                        gdpr_principle="Lawful basis for processing"
                    ))

    def _check_personal_data_storage(self, content: str, file_path: str):
        """
        GDPR Article 32 - Security of processing
        Check for secure personal data storage
        """
        # Look for unencrypted personal data storage
        insecure_storage_patterns = [
            (r'password\s*=.*(?!bcrypt|scrypt|argon)', 'Password stored without encryption'),
            (r'email.*=.*localStorage', 'Email stored in localStorage'),
            (r'ssn.*=.*localStorage', 'SSN stored in localStorage'),
            (r'creditCard.*=.*localStorage', 'Credit card stored in localStorage')
        ]

        for pattern, description in insecure_storage_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                self.issues.append(GDPRIssue(
                    article="Article 32",
                    severity="critical",
                    category="security",
                    description=description,
                    suggestion="Use encrypted storage or server-side storage for sensitive data",
                    gdpr_principle="Security of processing"
                ))

    def _create_result(self, skipped: bool = False, reason: str = "") -> Dict:
        """Create evaluation result dictionary"""
        if skipped:
            return {
                "gdpr_compliant": None,
                "gdpr_issues": 0,
                "skipped": True,
                "skip_reason": reason,
                "gdpr_compliance": {
                    "consent_management": "NOT_EVALUATED",
                    "data_minimization": "NOT_EVALUATED",
                    "right_to_erasure": "NOT_EVALUATED",
                    "privacy_by_design": "NOT_EVALUATED",
                    "cookie_consent": "NOT_EVALUATED",
                    "data_export": "NOT_EVALUATED"
                },
                "issues": []
            }

        # Categorize issues (Pattern #11: Single-pass categorization for O(n) vs O(4n))
        from collections import defaultdict
        issues_by_severity = defaultdict(list)
        for issue in self.issues:
            issues_by_severity[issue.severity].append(issue)

        critical_issues = issues_by_severity["critical"]
        high_issues = issues_by_severity["high"]
        medium_issues = issues_by_severity["medium"]
        low_issues = issues_by_severity["low"]

        # Determine compliance
        total_issues = len(self.issues)
        gdpr_compliant = len(critical_issues) == 0 and len(high_issues) == 0

        # Determine individual compliance areas
        category_checks = {
            "consent_management": not self._has_category("consent"),
            "data_minimization": not self._has_category("data_minimization"),
            "right_to_erasure": not self._has_category("right_to_erasure"),
            "privacy_by_design": not self._has_category("privacy_by_design"),
            "cookie_consent": not self._has_category("consent"),
            "data_export": not self._has_category("data_portability")
        }

        gdpr_compliance = {
            key: "PASS" if compliant else "FAIL"
            for key, compliant in category_checks.items()
        }

        return {
            "gdpr_compliant": gdpr_compliant,
            "gdpr_issues": total_issues,
            "critical_count": len(critical_issues),
            "high_count": len(high_issues),
            "medium_count": len(medium_issues),
            "low_count": len(low_issues),
            "gdpr_compliance": gdpr_compliance,
            "issues": [asdict(issue) for issue in self.issues]
        }

    def _has_category(self, category: str) -> bool:
        """Check if any issue matches the given category"""
        return any(issue.category == category for issue in self.issues)
