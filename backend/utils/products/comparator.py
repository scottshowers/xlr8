"""
XLR8 Schema Comparator
======================
Phase 5E: Compare schemas for M&A integration analysis.

This is the killer feature for M&A due diligence:
- Upload two system schemas
- Get instant integration gap analysis
- Identify overlapping entities, missing fields, naming differences

Usage:
    from backend.utils.products import compare_schemas, get_comparator
    
    # Compare two products
    result = compare_schemas('ukg_pro', 'workday_hcm')
    
    # Get detailed report
    print(result.summary())
    print(result.gap_analysis())

Deploy to: backend/utils/products/comparator.py
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

from .registry import get_registry, ProductSchema, ProductDomain
from .vocabulary import (
    get_vocabulary_normalizer, 
    get_domain_aligner,
    UNIVERSAL_ENTITIES,
    DOMAIN_TO_PRIMARY_ENTITY,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DomainComparison:
    """Comparison of a single domain between two products."""
    domain_name: str
    universal_entity: str  # Canonical entity (employee, compensation, etc.)
    
    # Source product
    source_domain: Optional[str] = None
    source_hubs: List[str] = field(default_factory=list)
    source_hub_count: int = 0
    
    # Target product
    target_domain: Optional[str] = None
    target_hubs: List[str] = field(default_factory=list)
    target_hub_count: int = 0
    
    # Comparison results
    status: str = 'unknown'  # 'matched', 'partial', 'source_only', 'target_only', 'missing'
    overlap_score: float = 0.0  # 0-1, how much overlap
    
    # Specific matches/gaps
    hub_matches: List[Tuple[str, str]] = field(default_factory=list)  # (source_hub, target_hub)
    source_only_hubs: List[str] = field(default_factory=list)
    target_only_hubs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'domain': self.domain_name,
            'entity': self.universal_entity,
            'status': self.status,
            'overlap_score': self.overlap_score,
            'source': {
                'domain': self.source_domain,
                'hub_count': self.source_hub_count,
            },
            'target': {
                'domain': self.target_domain,
                'hub_count': self.target_hub_count,
            },
            'matches': len(self.hub_matches),
            'source_only': len(self.source_only_hubs),
            'target_only': len(self.target_only_hubs),
        }


@dataclass
class SchemaComparison:
    """Complete comparison between two product schemas."""
    source_product: str
    target_product: str
    source_vendor: str
    target_vendor: str
    
    # Overall stats
    total_domains: int = 0
    matched_domains: int = 0
    partial_domains: int = 0
    source_only_domains: int = 0
    target_only_domains: int = 0
    
    total_source_hubs: int = 0
    total_target_hubs: int = 0
    matched_hubs: int = 0
    
    # Domain-level comparisons
    domain_comparisons: List[DomainComparison] = field(default_factory=list)
    
    # Overall scores
    compatibility_score: float = 0.0  # 0-1, overall integration compatibility
    complexity_score: float = 0.0     # 0-1, how complex is the integration
    risk_score: float = 0.0           # 0-1, integration risk
    
    # Recommendations
    integration_recommendations: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"# Schema Comparison: {self.source_vendor} → {self.target_vendor}",
            f"",
            f"## Overview",
            f"- Source: **{self.source_product}** ({self.total_source_hubs} hubs)",
            f"- Target: **{self.target_product}** ({self.total_target_hubs} hubs)",
            f"",
            f"## Compatibility",
            f"- **Overall Compatibility:** {self.compatibility_score:.0%}",
            f"- **Integration Complexity:** {self.complexity_score:.0%}",
            f"- **Risk Score:** {self.risk_score:.0%}",
            f"",
            f"## Domain Analysis",
            f"| Status | Count | % |",
            f"|--------|-------|---|",
            f"| Fully Matched | {self.matched_domains} | {self.matched_domains/max(self.total_domains,1)*100:.0f}% |",
            f"| Partially Matched | {self.partial_domains} | {self.partial_domains/max(self.total_domains,1)*100:.0f}% |",
            f"| Source Only | {self.source_only_domains} | {self.source_only_domains/max(self.total_domains,1)*100:.0f}% |",
            f"| Target Only | {self.target_only_domains} | {self.target_only_domains/max(self.total_domains,1)*100:.0f}% |",
            f"",
        ]
        
        if self.integration_recommendations:
            lines.append("## Recommendations")
            for rec in self.integration_recommendations:
                lines.append(f"- {rec}")
            lines.append("")
        
        if self.risk_factors:
            lines.append("## Risk Factors")
            for risk in self.risk_factors:
                lines.append(f"- ⚠️ {risk}")
            lines.append("")
        
        return "\n".join(lines)
    
    def gap_analysis(self) -> str:
        """Generate detailed gap analysis."""
        lines = [
            f"# Gap Analysis: {self.source_product} → {self.target_product}",
            f"",
        ]
        
        # Group by status
        by_status = defaultdict(list)
        for dc in self.domain_comparisons:
            by_status[dc.status].append(dc)
        
        # Source-only gaps (things in source not in target)
        if by_status.get('source_only'):
            lines.append("## Source-Only Domains (Migration Required)")
            lines.append("These domains exist in source but not target. Data migration strategy needed.")
            lines.append("")
            for dc in by_status['source_only']:
                lines.append(f"### {dc.domain_name}")
                lines.append(f"- Entity: {dc.universal_entity}")
                lines.append(f"- Source hubs: {dc.source_hub_count}")
                lines.append(f"- Hubs: {', '.join(dc.source_hubs[:5])}")
                if len(dc.source_hubs) > 5:
                    lines.append(f"  ...and {len(dc.source_hubs)-5} more")
                lines.append("")
        
        # Target-only gaps (things in target not in source)
        if by_status.get('target_only'):
            lines.append("## Target-Only Domains (New Capability)")
            lines.append("These domains exist in target but not source. Opportunity for improvement.")
            lines.append("")
            for dc in by_status['target_only']:
                lines.append(f"### {dc.domain_name}")
                lines.append(f"- Entity: {dc.universal_entity}")
                lines.append(f"- Target hubs: {dc.target_hub_count}")
                lines.append("")
        
        # Partial matches (complex mapping required)
        if by_status.get('partial'):
            lines.append("## Partial Matches (Mapping Required)")
            lines.append("These domains have some overlap but require careful mapping.")
            lines.append("")
            for dc in by_status['partial']:
                lines.append(f"### {dc.domain_name} ({dc.overlap_score:.0%} overlap)")
                lines.append(f"- Source: {dc.source_domain} ({dc.source_hub_count} hubs)")
                lines.append(f"- Target: {dc.target_domain} ({dc.target_hub_count} hubs)")
                if dc.hub_matches:
                    lines.append(f"- Matched hubs: {len(dc.hub_matches)}")
                if dc.source_only_hubs:
                    lines.append(f"- Source-only hubs: {', '.join(dc.source_only_hubs[:3])}")
                if dc.target_only_hubs:
                    lines.append(f"- Target-only hubs: {', '.join(dc.target_only_hubs[:3])}")
                lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        return {
            'source': {
                'product': self.source_product,
                'vendor': self.source_vendor,
                'hub_count': self.total_source_hubs,
            },
            'target': {
                'product': self.target_product,
                'vendor': self.target_vendor,
                'hub_count': self.total_target_hubs,
            },
            'scores': {
                'compatibility': self.compatibility_score,
                'complexity': self.complexity_score,
                'risk': self.risk_score,
            },
            'domains': {
                'total': self.total_domains,
                'matched': self.matched_domains,
                'partial': self.partial_domains,
                'source_only': self.source_only_domains,
                'target_only': self.target_only_domains,
            },
            'hubs': {
                'source_total': self.total_source_hubs,
                'target_total': self.total_target_hubs,
                'matched': self.matched_hubs,
            },
            'domain_details': [dc.to_dict() for dc in self.domain_comparisons],
            'recommendations': self.integration_recommendations,
            'risks': self.risk_factors,
        }


# =============================================================================
# SCHEMA COMPARATOR
# =============================================================================

class SchemaComparator:
    """
    Compares two product schemas for M&A integration analysis.
    
    Produces:
    - Domain-level gap analysis
    - Hub-level matching
    - Compatibility/risk scores
    - Integration recommendations
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.normalizer = get_vocabulary_normalizer()
        self.aligner = get_domain_aligner()
    
    def compare(self, source_id: str, target_id: str) -> SchemaComparison:
        """
        Compare two product schemas.
        
        Args:
            source_id: Source product ID (e.g., 'ukg_pro')
            target_id: Target product ID (e.g., 'workday_hcm')
            
        Returns:
            SchemaComparison with full analysis
        """
        # Load products
        source = self.registry.get_product(source_id)
        target = self.registry.get_product(target_id)
        
        if not source:
            raise ValueError(f"Source product not found: {source_id}")
        if not target:
            raise ValueError(f"Target product not found: {target_id}")
        
        # Initialize comparison
        comparison = SchemaComparison(
            source_product=source.product,
            target_product=target.product,
            source_vendor=source.vendor,
            target_vendor=target.vendor,
            total_source_hubs=source.hub_count,
            total_target_hubs=target.hub_count,
        )
        
        # Build domain comparisons
        self._compare_domains(source, target, comparison)
        
        # Calculate scores
        self._calculate_scores(comparison)
        
        # Generate recommendations
        self._generate_recommendations(comparison)
        
        return comparison
    
    def _compare_domains(self, source: ProductSchema, target: ProductSchema,
                        comparison: SchemaComparison):
        """Compare domains between source and target."""
        # Get all unique domain entities from both products
        source_entities = self._get_domain_entities(source)
        target_entities = self._get_domain_entities(target)
        
        all_entities = source_entities.keys() | target_entities.keys()
        comparison.total_domains = len(all_entities)
        
        for entity in all_entities:
            dc = DomainComparison(
                domain_name=entity.replace('_', ' ').title(),
                universal_entity=entity,
            )
            
            # Check source
            if entity in source_entities:
                src_info = source_entities[entity]
                dc.source_domain = src_info['domain']
                dc.source_hubs = src_info['hubs']
                dc.source_hub_count = len(src_info['hubs'])
            
            # Check target
            if entity in target_entities:
                tgt_info = target_entities[entity]
                dc.target_domain = tgt_info['domain']
                dc.target_hubs = tgt_info['hubs']
                dc.target_hub_count = len(tgt_info['hubs'])
            
            # Determine status and calculate overlap
            if dc.source_hubs and dc.target_hubs:
                # Both have this domain - calculate overlap
                matches, src_only, tgt_only = self._match_hubs(
                    dc.source_hubs, dc.target_hubs
                )
                dc.hub_matches = matches
                dc.source_only_hubs = src_only
                dc.target_only_hubs = tgt_only
                
                # Calculate overlap score
                total_unique = len(set(dc.source_hubs) | set(dc.target_hubs))
                dc.overlap_score = len(matches) / max(total_unique, 1)
                
                if dc.overlap_score >= 0.7:
                    dc.status = 'matched'
                    comparison.matched_domains += 1
                else:
                    dc.status = 'partial'
                    comparison.partial_domains += 1
                
                comparison.matched_hubs += len(matches)
                
            elif dc.source_hubs:
                dc.status = 'source_only'
                dc.source_only_hubs = dc.source_hubs
                comparison.source_only_domains += 1
                
            elif dc.target_hubs:
                dc.status = 'target_only'
                dc.target_only_hubs = dc.target_hubs
                comparison.target_only_domains += 1
            
            comparison.domain_comparisons.append(dc)
    
    def _get_domain_entities(self, product: ProductSchema) -> Dict[str, Dict]:
        """Get entity → domain/hubs mapping for a product."""
        result = {}
        
        for domain_name, domain in product.domains.items():
            # Get entity for this domain using vocabulary system
            entity = DOMAIN_TO_PRIMARY_ENTITY.get(domain_name)
            
            if not entity:
                # Try to infer from domain name
                domain_lower = domain_name.lower().replace('_', '')
                for ent, info in UNIVERSAL_ENTITIES.items():
                    # Check if domain name contains entity or vice versa
                    if ent in domain_lower or domain_lower in ent:
                        entity = ent
                        break
                    # Check against synonyms
                    for syn in info.get('synonyms', []):
                        if syn.replace(' ', '') in domain_lower:
                            entity = ent
                            break
                    if entity:
                        break
            
            if not entity:
                # Use cleaned domain name as entity (last resort)
                entity = domain_name.lower().replace('_', '')
            
            # Aggregate hubs under entity
            if entity not in result:
                result[entity] = {
                    'domain': domain_name,
                    'domains': [domain_name],  # Track all domains that map here
                    'hubs': [],
                }
            else:
                # Multiple domains map to same entity - aggregate
                result[entity]['domains'].append(domain_name)
            
            result[entity]['hubs'].extend(domain.hubs)
        
        return result
    
    def _match_hubs(self, source_hubs: List[str], 
                    target_hubs: List[str]) -> Tuple[List[Tuple], List[str], List[str]]:
        """Match hubs between source and target."""
        matches = []
        matched_source = set()
        matched_target = set()
        
        # Normalize hub names for comparison
        def normalize(hub: str) -> str:
            return hub.lower().replace('_', '').replace('-', '')
        
        source_normalized = {normalize(h): h for h in source_hubs}
        target_normalized = {normalize(h): h for h in target_hubs}
        
        # Exact matches (after normalization)
        for src_norm, src_orig in source_normalized.items():
            if src_norm in target_normalized:
                matches.append((src_orig, target_normalized[src_norm]))
                matched_source.add(src_orig)
                matched_target.add(target_normalized[src_norm])
        
        # Fuzzy matches for unmatched
        for src_orig in source_hubs:
            if src_orig in matched_source:
                continue
            src_norm = normalize(src_orig)
            
            for tgt_orig in target_hubs:
                if tgt_orig in matched_target:
                    continue
                tgt_norm = normalize(tgt_orig)
                
                # Check if one contains the other
                if src_norm in tgt_norm or tgt_norm in src_norm:
                    matches.append((src_orig, tgt_orig))
                    matched_source.add(src_orig)
                    matched_target.add(tgt_orig)
                    break
        
        source_only = [h for h in source_hubs if h not in matched_source]
        target_only = [h for h in target_hubs if h not in matched_target]
        
        return matches, source_only, target_only
    
    def _calculate_scores(self, comparison: SchemaComparison):
        """Calculate compatibility, complexity, and risk scores."""
        
        # Count entities with any overlap (even partial)
        entities_with_overlap = 0
        entities_with_good_overlap = 0
        total_entities_compared = 0
        
        for dc in comparison.domain_comparisons:
            if dc.source_hubs and dc.target_hubs:
                total_entities_compared += 1
                if dc.hub_matches:
                    entities_with_overlap += 1
                if dc.overlap_score >= 0.3:
                    entities_with_good_overlap += 1
        
        # Compatibility: weight both entity coverage and hub matching
        if comparison.total_domains > 0:
            # Entity coverage: what % of domains exist in both?
            entity_coverage = total_entities_compared / comparison.total_domains
            
            # Match quality: of shared domains, how many have good matches?
            match_quality = entities_with_overlap / max(total_entities_compared, 1)
            
            # Combined score
            comparison.compatibility_score = (entity_coverage * 0.6) + (match_quality * 0.4)
        
        # Complexity: based on unmapped hubs and partial matches
        if comparison.total_source_hubs > 0:
            unmapped_ratio = (comparison.total_source_hubs - comparison.matched_hubs) / \
                            comparison.total_source_hubs
            partial_ratio = comparison.partial_domains / max(comparison.total_domains, 1)
            comparison.complexity_score = (unmapped_ratio * 0.7) + (partial_ratio * 0.3)
        
        # Risk: low compatibility + high complexity
        comparison.risk_score = (1 - comparison.compatibility_score) * 0.4 + \
                               comparison.complexity_score * 0.6
    
    def _generate_recommendations(self, comparison: SchemaComparison):
        """Generate integration recommendations based on analysis."""
        recs = []
        risks = []
        
        # High compatibility
        if comparison.compatibility_score >= 0.7:
            recs.append("High domain overlap - straightforward integration path")
        elif comparison.compatibility_score >= 0.4:
            recs.append("Moderate domain overlap - custom mapping required for some areas")
        else:
            recs.append("Low domain overlap - significant integration effort expected")
            risks.append("Low compatibility may require extensive data transformation")
        
        # Source-only domains
        if comparison.source_only_domains > 0:
            pct = comparison.source_only_domains / comparison.total_domains * 100
            if pct > 30:
                risks.append(f"{comparison.source_only_domains} domains ({pct:.0f}%) exist only in source - data loss risk")
                recs.append("Evaluate which source-only domains are business-critical")
            else:
                recs.append(f"{comparison.source_only_domains} source-only domains - plan migration strategy")
        
        # Target-only domains
        if comparison.target_only_domains > 0:
            recs.append(f"{comparison.target_only_domains} new domains available in target - opportunity for improvement")
        
        # Hub matching
        if comparison.total_source_hubs > 0:
            match_pct = comparison.matched_hubs / comparison.total_source_hubs * 100
            if match_pct < 50:
                risks.append(f"Only {match_pct:.0f}% of source hubs have direct matches")
                recs.append("Detailed field-level mapping analysis recommended")
        
        # Complexity
        if comparison.complexity_score > 0.6:
            risks.append("High integration complexity - extended timeline recommended")
            recs.append("Consider phased migration approach")
        
        comparison.integration_recommendations = recs
        comparison.risk_factors = risks


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_comparator_instance: Optional[SchemaComparator] = None


def get_comparator() -> SchemaComparator:
    """Get the singleton comparator instance."""
    global _comparator_instance
    if _comparator_instance is None:
        _comparator_instance = SchemaComparator()
    return _comparator_instance


def compare_schemas(source_id: str, target_id: str) -> SchemaComparison:
    """Compare two product schemas."""
    return get_comparator().compare(source_id, target_id)


def quick_compare(source_id: str, target_id: str) -> Dict:
    """Quick comparison returning just the scores."""
    result = compare_schemas(source_id, target_id)
    return {
        'source': source_id,
        'target': target_id,
        'compatibility': f"{result.compatibility_score:.0%}",
        'complexity': f"{result.complexity_score:.0%}",
        'risk': f"{result.risk_score:.0%}",
        'matched_domains': result.matched_domains,
        'total_domains': result.total_domains,
    }
