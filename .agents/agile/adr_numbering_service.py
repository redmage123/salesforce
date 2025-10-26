#!/usr/bin/env python3
"""
ADRNumberingService (SOLID: Single Responsibility)

Single Responsibility: Manage ADR numbering and filename generation

This service handles ONLY ADR numbering logic:
- Getting next available ADR number
- Creating ADR filenames with proper formatting
"""

import re
from pathlib import Path
from typing import Optional


class ADRNumberingService:
    """
    Service for managing ADR numbering and filename generation

    Single Responsibility: ADR numbering and naming
    - Get next available ADR number by scanning directory
    - Create properly formatted ADR filenames
    - Handle filename sanitization
    """

    def __init__(self, adr_dir: Path):
        """
        Initialize ADR numbering service

        Args:
            adr_dir: Directory where ADRs are stored
        """
        self.adr_dir = adr_dir

    def get_next_adr_number(self) -> str:
        """
        Get next available ADR number by scanning existing ADRs

        Returns:
            ADR number as zero-padded string (e.g., "001", "002")
        """
        existing_adrs = list(self.adr_dir.glob("ADR-*.md"))
        if existing_adrs:
            numbers = []
            for adr_file in existing_adrs:
                match = re.search(r'ADR-(\d+)', adr_file.name)
                if match:
                    numbers.append(int(match.group(1)))
            next_num = max(numbers) + 1 if numbers else 1
        else:
            next_num = 1
        return f"{next_num:03d}"

    def create_adr_filename(self, title: str, adr_number: str) -> str:
        """
        Create ADR filename from title and number

        Sanitizes title to remove invalid characters and creates
        properly formatted ADR filename.

        Args:
            title: Task title (will be sanitized)
            adr_number: ADR number (e.g., "001")

        Returns:
            Formatted filename (e.g., "ADR-001-feature-name.md")
        """
        # Sanitize title to remove file paths and invalid characters
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title)  # Remove invalid chars
        slug = slug.lower().replace(' ', '-')[:50]  # Convert to kebab-case
        slug = re.sub(r'-+', '-', slug).strip('-')  # Normalize multiple dashes
        return f"ADR-{adr_number}-{slug}.md"
