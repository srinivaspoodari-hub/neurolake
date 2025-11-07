"""
AI-Powered Metadata Store - Intelligent metadata extraction using NeuroBrain
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class MetadataStore:
    """
    AI-Powered Metadata Store

    Uses NeuroBrain (LLM) for:
    - Automatic description generation
    - Intelligent tagging and classification
    - Semantic search
    - Business term extraction
    - Data quality insights
    - Column purpose inference
    """

    def __init__(self, storage_path: str = "./metadata_store", llm_client=None):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.llm_client = llm_client  # LLM client for AI features

        self.metadata: Dict[str, Dict] = {}
        self.embeddings: Dict[str, List[float]] = {}  # For semantic search

        self._load_metadata()

    def _load_metadata(self):
        """Load metadata from storage"""
        metadata_file = self.storage_path / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    self.metadata = data.get('metadata', {})
                logger.info(f"Loaded metadata for {len(self.metadata)} assets")
            except Exception as e:
                logger.error(f"Error loading metadata: {e}")

    def _save_metadata(self):
        """Save metadata to storage"""
        metadata_file = self.storage_path / "metadata.json"
        try:
            with open(metadata_file, 'w') as f:
                json.dump({
                    'metadata': self.metadata
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")

    def generate_description(self, asset_id: str, asset_data: Dict) -> str:
        """
        Use AI to generate a description for an asset

        Args:
            asset_id: Asset identifier
            asset_data: Asset data (table name, columns, sample data, etc.)
        """
        if not self.llm_client:
            return self._generate_basic_description(asset_data)

        try:
            prompt = self._build_description_prompt(asset_data)
            description = self.llm_client.generate(prompt)
            return description
        except Exception as e:
            logger.error(f"Error generating AI description: {e}")
            return self._generate_basic_description(asset_data)

    def _build_description_prompt(self, asset_data: Dict) -> str:
        """Build prompt for AI description generation"""
        asset_type = asset_data.get('asset_type', 'unknown')
        name = asset_data.get('name', 'unknown')

        prompt = f"""Generate a concise description for this {asset_type}: {name}

Asset Information:
"""

        if 'columns' in asset_data:
            prompt += f"Columns: {', '.join([col.get('name', '') for col in asset_data['columns']])}\n"

        if 'sample_data' in asset_data:
            prompt += f"Sample Data: {asset_data['sample_data']}\n"

        prompt += "\nProvide a 1-2 sentence description of what this asset contains and its purpose."

        return prompt

    def _generate_basic_description(self, asset_data: Dict) -> str:
        """Generate a basic description without AI"""
        asset_type = asset_data.get('asset_type', 'data asset')
        name = asset_data.get('name', 'unknown')

        if 'columns' in asset_data and len(asset_data['columns']) > 0:
            col_count = len(asset_data['columns'])
            return f"A {asset_type} named {name} with {col_count} columns"

        return f"A {asset_type} named {name}"

    def suggest_tags(self, asset_id: str, asset_data: Dict) -> List[str]:
        """
        Use AI to suggest relevant tags for an asset

        Returns list of suggested tags based on content analysis
        """
        if not self.llm_client:
            return self._suggest_basic_tags(asset_data)

        try:
            prompt = self._build_tagging_prompt(asset_data)
            tags_response = self.llm_client.generate(prompt)

            # Parse tags from response (assume comma-separated)
            tags = [tag.strip() for tag in tags_response.split(',')]
            return tags[:10]  # Limit to 10 tags
        except Exception as e:
            logger.error(f"Error generating AI tags: {e}")
            return self._suggest_basic_tags(asset_data)

    def _build_tagging_prompt(self, asset_data: Dict) -> str:
        """Build prompt for AI tag suggestion"""
        name = asset_data.get('name', '')
        description = asset_data.get('description', '')
        columns = asset_data.get('columns', [])

        prompt = f"""Suggest relevant tags for this data asset:

Name: {name}
Description: {description}
"""

        if columns:
            col_names = ', '.join([col.get('name', '') for col in columns])
            prompt += f"Columns: {col_names}\n"

        prompt += "\nProvide 5-10 relevant tags (comma-separated) that classify this asset. Tags should include: domain, data type, purpose, sensitivity level, etc."

        return prompt

    def _suggest_basic_tags(self, asset_data: Dict) -> List[str]:
        """Suggest basic tags without AI"""
        tags = []
        asset_type = asset_data.get('asset_type', '')
        if asset_type:
            tags.append(asset_type)

        name = asset_data.get('name', '').lower()

        # Rule-based tag suggestions
        if 'customer' in name or 'user' in name:
            tags.extend(['customer', 'user-data'])
        if 'transaction' in name or 'order' in name:
            tags.extend(['transactional', 'financial'])
        if 'log' in name or 'event' in name:
            tags.extend(['logs', 'events'])
        if 'dim_' in name:
            tags.append('dimension')
        if 'fact_' in name:
            tags.append('fact')

        return list(set(tags))

    def infer_column_purpose(self, column_name: str, data_type: str, sample_values: List[Any] = None) -> Dict:
        """
        Use AI to infer the purpose of a column

        Returns:
            {
                "purpose": "description of what this column contains",
                "business_term": "suggested business term",
                "sensitive": true/false,
                "pii": true/false
            }
        """
        if not self.llm_client:
            return self._infer_basic_column_purpose(column_name, data_type)

        try:
            prompt = f"""Analyze this database column:

Column Name: {column_name}
Data Type: {data_type}
"""

            if sample_values:
                prompt += f"Sample Values: {sample_values[:5]}\n"

            prompt += """
Provide:
1. Purpose: What does this column contain?
2. Business Term: What would business users call this?
3. Sensitive: Is this sensitive data? (yes/no)
4. PII: Does this contain personally identifiable information? (yes/no)

Format as JSON.
"""

            response = self.llm_client.generate(prompt)
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return self._infer_basic_column_purpose(column_name, data_type)

        except Exception as e:
            logger.error(f"Error inferring column purpose: {e}")
            return self._infer_basic_column_purpose(column_name, data_type)

    def _infer_basic_column_purpose(self, column_name: str, data_type: str) -> Dict:
        """Infer column purpose using rules"""
        col_lower = column_name.lower()

        purpose = f"Column containing {data_type} data"
        business_term = column_name.replace('_', ' ').title()
        sensitive = False
        pii = False

        # PII detection
        pii_keywords = ['email', 'ssn', 'phone', 'address', 'name', 'dob', 'birthdate', 'passport']
        if any(keyword in col_lower for keyword in pii_keywords):
            pii = True
            sensitive = True

        # Sensitive data detection
        sensitive_keywords = ['salary', 'password', 'credit', 'card', 'bank', 'account']
        if any(keyword in col_lower for keyword in sensitive_keywords):
            sensitive = True

        return {
            'purpose': purpose,
            'business_term': business_term,
            'sensitive': sensitive,
            'pii': pii
        }

    def semantic_search(self, query: str, top_k: int = 10) -> List[str]:
        """
        Semantic search across metadata using embeddings

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of asset IDs ranked by semantic similarity
        """
        if not self.llm_client or not hasattr(self.llm_client, 'embed'):
            # Fallback to keyword search
            return self._keyword_search(query, top_k)

        try:
            query_embedding = self.llm_client.embed(query)

            # Calculate similarity scores
            scores = []
            for asset_id, embedding in self.embeddings.items():
                similarity = self._cosine_similarity(query_embedding, embedding)
                scores.append((asset_id, similarity))

            # Sort by similarity and return top_k
            scores.sort(key=lambda x: x[1], reverse=True)
            return [asset_id for asset_id, _ in scores[:top_k]]

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return self._keyword_search(query, top_k)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _keyword_search(self, query: str, top_k: int) -> List[str]:
        """Fallback keyword-based search"""
        query_lower = query.lower()
        results = []

        for asset_id, meta in self.metadata.items():
            score = 0
            searchable = f"{meta.get('name', '')} {meta.get('description', '')} {' '.join(meta.get('tags', []))}"
            searchable = searchable.lower()

            # Count keyword matches
            for word in query_lower.split():
                if word in searchable:
                    score += 1

            if score > 0:
                results.append((asset_id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [asset_id for asset_id, _ in results[:top_k]]

    def enrich_metadata(self, asset_id: str, asset_data: Dict) -> Dict:
        """
        Enrich asset metadata using AI

        Generates description, tags, and insights
        """
        enriched = {
            'asset_id': asset_id,
            'original_data': asset_data,
            'ai_generated_description': self.generate_description(asset_id, asset_data),
            'suggested_tags': self.suggest_tags(asset_id, asset_data),
            'enriched_at': datetime.utcnow().isoformat()
        }

        # Enrich columns if present
        if 'columns' in asset_data:
            enriched['enriched_columns'] = []
            for col in asset_data['columns']:
                col_enriched = self.infer_column_purpose(
                    col.get('name', ''),
                    col.get('type', 'string'),
                    col.get('sample_values', [])
                )
                enriched['enriched_columns'].append({
                    **col,
                    **col_enriched
                })

        self.metadata[asset_id] = enriched
        self._save_metadata()

        return enriched
