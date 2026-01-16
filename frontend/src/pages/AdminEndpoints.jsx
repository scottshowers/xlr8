/**
 * AdminEndpoints.jsx
 * ===================
 * 
 * Reference page for all API endpoints - kept up to date by Claude
 * 
 * Deploy to: frontend/src/pages/AdminEndpoints.jsx
 * 
 * Last Updated: January 4, 2026
 * Visual Standards: Part 13 - lucide icons
 * Total Endpoints: 259
 */

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, ExternalLink, Copy, Check, Search, Rocket, Heart, Upload,
  Clock, ClipboardList, Folder, FileText, BarChart3, Brain, MessageSquare,
  Wrench, Settings, Plug, Link2, ScrollText, Database, Shield, ChevronDown,
  Tag, BookOpen, Key, Target, Trash2, TrendingUp, Lock
} from 'lucide-react';

// Icon mapping for categories (lucide icons instead of emojis)
const CATEGORY_ICONS = {
  platform: Rocket,
  health: Heart,
  upload: Upload,
  progress: Clock,
  jobs: ClipboardList,
  projects: Folder,
  files: FileText,
  classification: Search,
  domains: Tag,
  chat: MessageSquare,
  query: BarChart3,
  intelligence: Brain,
  relationships: Link2,
  regulatory: ScrollText,
  reference: BookOpen,
  maintenance: Wrench,
  library: Database,
  auth: Key,
  standards: ClipboardList,
  metrics: TrendingUp,
  cleanup: Trash2,
  admin: Settings,
  security: Lock,
  security_new: Shield,
  llm: Target,
  integration: Plug,
  logs: FileText,
  vacuum: Trash2,
  export: Upload,
};

const PRODUCTION_URL = 'https://hcmpact-xlr8-production.up.railway.app';

const ENDPOINT_CATEGORIES = [
  {
    id: 'platform',
    name: 'Platform (Primary)',

    description: 'Comprehensive platform status - USE THIS for dashboards',
    endpoints: [
      { method: 'GET', path: '/api/platform', description: 'COMPREHENSIVE status. Use ?include=files,relationships for full data', priority: 'high' },
      { method: 'GET', path: '/api/platform/health', description: 'Quick health check only', priority: 'high' },
      { method: 'GET', path: '/api/platform/stats', description: 'Stats only (for dashboard cards)', priority: 'medium' },
    ]
  },
  {
    id: 'health',
    name: 'Health & System',

    description: 'System health checks, diagnostics, and operational status (18 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/health', description: 'Full system health check with all subsystems', priority: 'high' },
      { method: 'GET', path: '/api/health/operational', description: 'Operational health with recommendations', priority: 'high' },
      { method: 'GET', path: '/api/health/integrity', description: 'Data integrity check (orphans, mismatches)', priority: 'high' },
      { method: 'GET', path: '/api/health/duckdb', description: 'DuckDB health and table stats', priority: 'medium' },
      { method: 'GET', path: '/api/health/chromadb', description: 'ChromaDB health and chunk stats', priority: 'medium' },
      { method: 'GET', path: '/api/health/supabase', description: 'Supabase connection health', priority: 'medium' },
      { method: 'GET', path: '/api/health/llm', description: 'LLM provider health', priority: 'medium' },
      { method: 'GET', path: '/api/health/jobs', description: 'Job queue health', priority: 'medium' },
      { method: 'GET', path: '/api/health/files', description: 'File system health', priority: 'low' },
      { method: 'GET', path: '/api/health/projects', description: 'All projects health', priority: 'low' },
      { method: 'GET', path: '/api/health/project/{project_name}', description: 'Single project detail', priority: 'low', param: 'project_name' },
      { method: 'GET', path: '/api/health/duplicates', description: 'Find duplicate files', priority: 'low' },
      { method: 'GET', path: '/api/health/stale-files', description: 'Find stale files', priority: 'low' },
      { method: 'GET', path: '/api/health/uploaders', description: 'Uploader stats', priority: 'low' },
      { method: 'GET', path: '/api/health/lineage', description: 'Data lineage summary', priority: 'low' },
      { method: 'GET', path: '/api/health/lineage/project/{project_name}', description: 'Project lineage', priority: 'low', param: 'project_name' },
      { method: 'GET', path: '/api/health/lineage/{node_type}/{node_id}', description: 'Node lineage', priority: 'low', param: 'node_type, node_id' },
      { method: 'GET', path: '/api/health/lineage/trace/{target_type}/{target_id}', description: 'Trace to source', priority: 'low', param: 'target_type, target_id' },
      { method: 'GET', path: '/api/debug/imports', description: 'Check module imports', priority: 'low' },
    ]
  },
  {
    id: 'upload',
    name: 'Upload & Processing',

    description: 'File upload and processing (5 endpoints)',
    endpoints: [
      { method: 'POST', path: '/api/upload', description: 'Smart upload - auto-routes to correct processor', priority: 'high' },
      { method: 'GET', path: '/api/upload/status/{job_id}', description: 'Get job processing status', priority: 'high', param: 'job_id' },
      { method: 'GET', path: '/api/upload/queue-status', description: 'Current upload queue status', priority: 'medium' },
      { method: 'GET', path: '/api/upload/router-status', description: 'Upload router configuration', priority: 'low' },
      { method: 'GET', path: '/api/upload/debug', description: 'Debug upload features', priority: 'low' },
    ]
  },
  {
    id: 'progress',
    name: 'Job Progress',

    description: 'Real-time job progress tracking (3 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/progress/{job_id}', description: 'Get job progress', priority: 'high', param: 'job_id' },
      { method: 'GET', path: '/api/progress/stream/{job_id}', description: 'SSE progress stream', priority: 'high', param: 'job_id' },
      { method: 'GET', path: '/api/progress/active', description: 'List active jobs', priority: 'medium' },
    ]
  },
  {
    id: 'jobs',
    name: 'Job Management',

    description: 'Job history and management (9 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/jobs', description: 'List all jobs', priority: 'high' },
      { method: 'GET', path: '/api/jobs/{job_id}', description: 'Get job details', priority: 'medium', param: 'job_id' },
      { method: 'POST', path: '/api/jobs/{job_id}/cancel', description: 'Cancel running job', priority: 'medium', param: 'job_id' },
      { method: 'POST', path: '/api/jobs/cleanup', description: 'Cleanup stuck jobs', priority: 'medium' },
      { method: 'DELETE', path: '/api/jobs/{job_id}', description: 'Delete single job', priority: 'low', param: 'job_id', dangerous: true },
      { method: 'DELETE', path: '/api/jobs', description: 'Clear job history', priority: 'low', dangerous: true },
      { method: 'POST', path: '/api/jobs/clear-all', description: 'Delete all jobs', priority: 'low', dangerous: true },
    ]
  },
  {
    id: 'projects',
    name: 'Projects',

    description: 'Project management (5 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/projects/list', description: 'List all projects', priority: 'high' },
      { method: 'GET', path: '/api/projects/{project_id}', description: 'Get project details', priority: 'medium', param: 'project_id' },
      { method: 'POST', path: '/api/projects/create', description: 'Create new project', priority: 'medium' },
      { method: 'PUT', path: '/api/projects/{project_id}', description: 'Update project', priority: 'low', param: 'project_id' },
      { method: 'DELETE', path: '/api/projects/{project_id}', description: 'Delete project', priority: 'low', param: 'project_id', dangerous: true },
    ]
  },
  {
    id: 'files',
    name: 'Files & Status',

    description: 'File listing and status (8 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/files', description: 'Fast file listing', priority: 'high' },
      { method: 'GET', path: '/api/status/structured', description: 'List structured files (DuckDB)', priority: 'medium' },
      { method: 'GET', path: '/api/status/documents', description: 'List documents (ChromaDB)', priority: 'medium' },
      { method: 'GET', path: '/api/status/references', description: 'List reference documents', priority: 'medium' },
      { method: 'GET', path: '/api/status/chromadb', description: 'ChromaDB status', priority: 'medium' },
      { method: 'GET', path: '/api/status/data-integrity', description: 'Data integrity check', priority: 'medium' },
      { method: 'GET', path: '/api/status/table-profile/{table_name}', description: 'Get table profile', priority: 'low', param: 'table_name' },
      { method: 'POST', path: '/api/status/refresh-metrics', description: 'Refresh metrics cache', priority: 'low' },
    ]
  },
  {
    id: 'classification',
    name: 'Classification (FIVE TRUTHS)',

    description: 'Table/column classification and transparency (9 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/classification/health', description: 'Classification service health', priority: 'high' },
      { method: 'GET', path: '/api/classification/tables', description: 'All tables with classification', priority: 'high' },
      { method: 'GET', path: '/api/classification/table/{table_name}', description: 'Full table classification', priority: 'high', param: 'table_name' },
      { method: 'GET', path: '/api/classification/column/{table_name}/{column_name}', description: 'Column detail', priority: 'medium', param: 'table_name, column_name' },
      { method: 'GET', path: '/api/classification/chunks', description: 'Documents with chunk counts', priority: 'medium' },
      { method: 'GET', path: '/api/classification/chunks/{document_name}', description: 'Document chunks', priority: 'medium', param: 'document_name' },
      { method: 'GET', path: '/api/classification/routing', description: 'Routing decisions (debug)', priority: 'low' },
      { method: 'POST', path: '/api/classification/reclassify/table', description: 'Reclassify table', priority: 'low' },
      { method: 'POST', path: '/api/classification/reclassify/column', description: 'Reclassify column', priority: 'low' },
    ]
  },
  {
    id: 'custom-domains',
    name: 'Custom Domains',

    description: 'Custom domain definitions (3 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/custom-domains', description: 'List custom domains', priority: 'medium' },
      { method: 'POST', path: '/api/custom-domains', description: 'Create custom domain', priority: 'medium' },
      { method: 'DELETE', path: '/api/custom-domains/{domain_name}', description: 'Delete domain', priority: 'low', param: 'domain_name', dangerous: true },
    ]
  },
  {
    id: 'chat',
    name: 'Chat & Analysis',

    description: 'Unified chat and query (25 endpoints)',
    endpoints: [
      { method: 'POST', path: '/api/chat/unified', description: 'Main chat - FIVE TRUTHS analysis', priority: 'high' },
      { method: 'GET', path: '/api/chat/unified/health', description: 'Chat service health', priority: 'high' },
      { method: 'GET', path: '/api/chat/unified/stats', description: 'Chat usage stats', priority: 'medium' },
      { method: 'GET', path: '/api/chat/unified/diagnostics', description: 'Chat diagnostics', priority: 'medium' },
      { method: 'POST', path: '/api/chat/unified/clarify', description: 'Submit clarification', priority: 'medium' },
      { method: 'POST', path: '/api/chat/unified/feedback', description: 'Submit feedback', priority: 'medium' },
      { method: 'POST', path: '/api/chat/unified/export-excel', description: 'Export to Excel', priority: 'medium' },
      { method: 'GET', path: '/api/chat/unified/data/{project}', description: 'Project data summary', priority: 'medium', param: 'project' },
      { method: 'GET', path: '/api/chat/unified/preferences', description: 'Get preferences', priority: 'low' },
      { method: 'POST', path: '/api/chat/unified/reset-preferences', description: 'Reset preferences', priority: 'low' },
      { method: 'GET', path: '/api/chat/unified/personas', description: 'List personas', priority: 'low' },
      { method: 'POST', path: '/api/chat/unified/personas', description: 'Create persona', priority: 'low' },
      { method: 'GET', path: '/api/chat/unified/personas/{name}', description: 'Get persona', priority: 'low', param: 'name' },
      { method: 'PUT', path: '/api/chat/unified/personas/{name}', description: 'Update persona', priority: 'low', param: 'name' },
      { method: 'DELETE', path: '/api/chat/unified/personas/{name}', description: 'Delete persona', priority: 'low', param: 'name' },
      { method: 'GET', path: '/api/chat/models', description: 'Available models', priority: 'low' },
    ]
  },
  {
    id: 'bi',
    name: 'BI Builder',

    description: 'Business Intelligence query builder (8 endpoints)',
    endpoints: [
      { method: 'POST', path: '/api/bi/query', description: 'Execute BI query', priority: 'high' },
      { method: 'GET', path: '/api/bi/schema/{project}', description: 'Get project schema', priority: 'high', param: 'project' },
      { method: 'GET', path: '/api/bi/suggestions/{project}', description: 'Query suggestions', priority: 'medium', param: 'project' },
      { method: 'POST', path: '/api/bi/execute', description: 'Execute raw SQL', priority: 'medium' },
      { method: 'POST', path: '/api/bi/export', description: 'Export BI results', priority: 'medium' },
      { method: 'POST', path: '/api/bi/saved', description: 'Save query', priority: 'low' },
      { method: 'GET', path: '/api/bi/saved/{project}', description: 'Get saved queries', priority: 'low', param: 'project' },
      { method: 'DELETE', path: '/api/bi/saved/{query_id}', description: 'Delete saved query', priority: 'low', param: 'query_id' },
    ]
  },
  {
    id: 'intelligence',
    name: 'Intelligence Engine',

    description: 'Project analysis and insights (13 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/intelligence/health', description: 'Engine health', priority: 'high' },
      { method: 'POST', path: '/api/intelligence/{project}/analyze', description: 'Full project analysis', priority: 'high', param: 'project' },
      { method: 'GET', path: '/api/intelligence/{project}/summary', description: 'Project summary', priority: 'high', param: 'project' },
      { method: 'GET', path: '/api/intelligence/{project}/findings', description: 'Analysis findings', priority: 'high', param: 'project' },
      { method: 'GET', path: '/api/intelligence/{project}/tasks', description: 'Recommended tasks', priority: 'medium', param: 'project' },
      { method: 'POST', path: '/api/intelligence/{project}/task/{task_id}/complete', description: 'Complete task', priority: 'medium', param: 'project, task_id' },
      { method: 'GET', path: '/api/intelligence/{project}/relationships', description: 'Detected relationships', priority: 'medium', param: 'project' },
      { method: 'GET', path: '/api/intelligence/{project}/lookups', description: 'Lookup tables', priority: 'medium', param: 'project' },
      { method: 'GET', path: '/api/intelligence/{project}/evidence/{finding_id}', description: 'Finding evidence', priority: 'medium', param: 'project, finding_id' },
      { method: 'GET', path: '/api/intelligence/{project}/decode/{column}/{value}', description: 'Decode value', priority: 'low', param: 'project, column, value' },
      { method: 'POST', path: '/api/intelligence/{project}/collision-check', description: 'Check collisions', priority: 'low', param: 'project' },
      { method: 'POST', path: '/api/intelligence/{project}/stuck', description: 'Help when stuck', priority: 'low', param: 'project' },
      { method: 'GET', path: '/api/intelligence/{project}/work-trail', description: 'Work trail', priority: 'low', param: 'project' },
    ]
  },
  {
    id: 'data-model',
    name: 'Data Model',

    description: 'Relationship detection and data modeling (12 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/data-model/projects', description: 'Projects with data', priority: 'high' },
      { method: 'GET', path: '/api/data-model/relationships/{project_name}', description: 'Get relationships', priority: 'high', param: 'project_name' },
      { method: 'GET', path: '/api/data-model/relationships-summary', description: 'All relationships summary', priority: 'medium' },
      { method: 'POST', path: '/api/data-model/analyze/{project_name}', description: 'Analyze data model', priority: 'medium', param: 'project_name' },
      { method: 'POST', path: '/api/data-model/analyze-all', description: 'Analyze all projects', priority: 'low' },
      { method: 'POST', path: '/api/data-model/relationships/{project_name}/create', description: 'Create relationship', priority: 'medium', param: 'project_name' },
      { method: 'POST', path: '/api/data-model/relationships/{project_name}/confirm', description: 'Confirm relationship', priority: 'medium', param: 'project_name' },
      { method: 'PATCH', path: '/api/data-model/relationships/{rel_id}', description: 'Update relationship', priority: 'low', param: 'rel_id' },
      { method: 'DELETE', path: '/api/data-model/relationships/{project_name}', description: 'Delete relationship', priority: 'low', param: 'project_name', dangerous: true },
      { method: 'DELETE', path: '/api/data-model/relationships/{project_name}/all', description: 'Delete all relationships', priority: 'low', param: 'project_name', dangerous: true },
      { method: 'POST', path: '/api/data-model/test-relationship', description: 'Test relationship', priority: 'low' },
      { method: 'GET', path: '/api/data-model/table-preview/{project}/{table_name}', description: 'Preview table', priority: 'low', param: 'project, table_name' },
    ]
  },
  {
    id: 'compare',
    name: 'Table Compare',

    description: 'Compare tables (2 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/compare/tables', description: 'List comparable tables', priority: 'medium' },
      { method: 'POST', path: '/api/compare', description: 'Compare two tables', priority: 'medium' },
    ]
  },
  {
    id: 'playbooks',
    name: 'Playbooks',

    description: 'Year-end and custom playbooks (21 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/playbooks/health', description: 'Playbooks health', priority: 'high' },
      { method: 'GET', path: '/api/playbooks/year-end/structure', description: 'Playbook structure', priority: 'high' },
      { method: 'POST', path: '/api/playbooks/year-end/refresh-structure', description: 'Refresh structure', priority: 'medium' },
      { method: 'GET', path: '/api/playbooks/year-end/progress/{project_id}', description: 'Get progress', priority: 'high', param: 'project_id' },
      { method: 'POST', path: '/api/playbooks/year-end/progress/{project_id}', description: 'Update progress', priority: 'medium', param: 'project_id' },
      { method: 'POST', path: '/api/playbooks/year-end/scan/{project_id}/{action_id}', description: 'Scan for action', priority: 'high', param: 'project_id, action_id' },
      { method: 'POST', path: '/api/playbooks/year-end/scan-all/{project_id}', description: 'Scan all actions', priority: 'medium', param: 'project_id' },
      { method: 'GET', path: '/api/playbooks/year-end/scan-all/status/{job_id}', description: 'Scan-all status', priority: 'medium', param: 'job_id' },
      { method: 'GET', path: '/api/playbooks/year-end/summary/{project_id}', description: 'AI summary', priority: 'medium', param: 'project_id' },
      { method: 'GET', path: '/api/playbooks/year-end/entity-config/{project_id}', description: 'Entity config', priority: 'medium', param: 'project_id' },
      { method: 'POST', path: '/api/playbooks/year-end/entity-config/{project_id}', description: 'Set entity config', priority: 'medium', param: 'project_id' },
      { method: 'GET', path: '/api/playbooks/year-end/document-checklist/{project_id}', description: 'Document checklist', priority: 'medium', param: 'project_id' },
      { method: 'GET', path: '/api/playbooks/year-end/export/{project_id}', description: 'Export results', priority: 'medium', param: 'project_id' },
      { method: 'POST', path: '/api/playbooks/year-end/feedback/{project_id}/{action_id}', description: 'Record feedback', priority: 'low', param: 'project_id, action_id' },
      { method: 'GET', path: '/api/playbooks/year-end/suppressions/{project_id}', description: 'Get suppressions', priority: 'low', param: 'project_id' },
      { method: 'POST', path: '/api/playbooks/year-end/suppress/{project_id}', description: 'Suppress finding', priority: 'low', param: 'project_id' },
      { method: 'POST', path: '/api/playbooks/year-end/suppress/quick/{project_id}/{action_id}', description: 'Quick suppress', priority: 'low', param: 'project_id, action_id' },
      { method: 'POST', path: '/api/playbooks/{playbook_type}/detect-entities/{project_id}', description: 'Detect entities', priority: 'low', param: 'playbook_type, project_id' },
      { method: 'GET', path: '/api/playbooks/learning/stats', description: 'Learning stats', priority: 'low' },
      { method: 'GET', path: '/api/playbooks/learning/patterns/{playbook_id}', description: 'Learning patterns', priority: 'low', param: 'playbook_id' },
    ]
  },
  {
    id: 'playbook-builder',
    name: 'Playbook Builder',

    description: 'Custom playbook configuration (9 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/playbook-builder/health', description: 'Builder health', priority: 'high' },
      { method: 'GET', path: '/api/playbook-builder/configs', description: 'List configs', priority: 'high' },
      { method: 'POST', path: '/api/playbook-builder/configs', description: 'Create config', priority: 'medium' },
      { method: 'GET', path: '/api/playbook-builder/configs/{playbook_id}', description: 'Get config', priority: 'medium', param: 'playbook_id' },
      { method: 'PUT', path: '/api/playbook-builder/configs/{playbook_id}', description: 'Update config', priority: 'medium', param: 'playbook_id' },
      { method: 'DELETE', path: '/api/playbook-builder/configs/{playbook_id}', description: 'Delete config', priority: 'low', param: 'playbook_id', dangerous: true },
      { method: 'POST', path: '/api/playbook-builder/configs/{playbook_id}/toggle', description: 'Toggle active', priority: 'low', param: 'playbook_id' },
      { method: 'POST', path: '/api/playbook-builder/clone', description: 'Clone playbook', priority: 'low' },
      { method: 'GET', path: '/api/playbook-builder/components', description: 'List components', priority: 'low' },
    ]
  },
  {
    id: 'reference',
    name: 'Reference Data',

    description: 'Systems, vendors, domains (16 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/reference/systems', description: 'List HCM systems', priority: 'high' },
      { method: 'GET', path: '/api/reference/systems/{code}', description: 'Get system', priority: 'medium', param: 'code' },
      { method: 'GET', path: '/api/reference/vendors', description: 'List vendors', priority: 'medium' },
      { method: 'GET', path: '/api/reference/domains', description: 'List domains', priority: 'medium' },
      { method: 'GET', path: '/api/reference/domains/{code}', description: 'Get domain', priority: 'low', param: 'code' },
      { method: 'GET', path: '/api/reference/functional-areas', description: 'List functional areas', priority: 'medium' },
      { method: 'GET', path: '/api/reference/functional-areas/grouped', description: 'Grouped areas', priority: 'low' },
      { method: 'GET', path: '/api/reference/engagement-types', description: 'Engagement types', priority: 'low' },
      { method: 'GET', path: '/api/reference/stats', description: 'Reference stats', priority: 'low' },
      { method: 'POST', path: '/api/reference/detect', description: 'Detect context', priority: 'medium' },
      { method: 'GET', path: '/api/reference/projects/{project_id}/context', description: 'Project context', priority: 'medium', param: 'project_id' },
      { method: 'POST', path: '/api/reference/projects/{project_id}/detect', description: 'Run detection', priority: 'medium', param: 'project_id' },
      { method: 'POST', path: '/api/reference/projects/{project_id}/context/confirm', description: 'Confirm context', priority: 'low', param: 'project_id' },
      { method: 'GET', path: '/api/reference/admin/signatures', description: 'Detection signatures', priority: 'low' },
      { method: 'POST', path: '/api/reference/admin/signatures', description: 'Create signature', priority: 'low' },
      { method: 'DELETE', path: '/api/reference/admin/signatures/{signature_id}', description: 'Delete signature', priority: 'low', param: 'signature_id', dangerous: true },
    ]
  },
  {
    id: 'decoder',
    name: 'Domain Decoder',

    description: 'Domain knowledge and code decoding (10 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/decoder/decode', description: 'Decode text/codes', priority: 'high' },
      { method: 'GET', path: '/api/decoder', description: 'List all knowledge', priority: 'medium' },
      { method: 'POST', path: '/api/decoder', description: 'Add knowledge', priority: 'medium' },
      { method: 'GET', path: '/api/decoder/search', description: 'Search knowledge', priority: 'medium' },
      { method: 'GET', path: '/api/decoder/category/{category}', description: 'Get by category', priority: 'low', param: 'category' },
      { method: 'GET', path: '/api/decoder/domain/{domain}', description: 'Get by domain', priority: 'low', param: 'domain' },
      { method: 'GET', path: '/api/decoder/meta', description: 'Decoder metadata', priority: 'low' },
      { method: 'POST', path: '/api/decoder/seed', description: 'Seed knowledge', priority: 'low' },
      { method: 'PUT', path: '/api/decoder/{entry_id}', description: 'Update entry', priority: 'low', param: 'entry_id' },
      { method: 'DELETE', path: '/api/decoder/{entry_id}', description: 'Delete entry', priority: 'low', param: 'entry_id', dangerous: true },
    ]
  },
  {
    id: 'standards',
    name: 'Standards',

    description: 'Standards and compliance (5 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/standards/health', description: 'Standards health', priority: 'high' },
      { method: 'GET', path: '/api/standards/documents', description: 'List documents', priority: 'medium' },
      { method: 'GET', path: '/api/standards/rules', description: 'List rules', priority: 'medium' },
      { method: 'POST', path: '/api/standards/upload', description: 'Upload standards', priority: 'medium' },
      { method: 'POST', path: '/api/standards/compliance/check/{project_id}', description: 'Run compliance check', priority: 'medium', param: 'project_id' },
    ]
  },
  {
    id: 'metrics',
    name: 'Metrics & Analytics',

    description: 'Platform metrics, costs, analytics (16 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/metrics/summary', description: 'Platform summary', priority: 'high' },
      { method: 'GET', path: '/api/metrics/health', description: 'Metrics health', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/trends', description: 'Time-series metrics', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/throughput', description: 'Hourly throughput', priority: 'high' },
      { method: 'GET', path: '/api/metrics/activity', description: 'Recent activity', priority: 'high' },
      { method: 'GET', path: '/api/metrics/upload-history', description: 'Upload history', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/processors', description: 'Processor breakdown', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/llm', description: 'LLM usage', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/costs', description: 'Cost summary (30d)', priority: 'high' },
      { method: 'GET', path: '/api/metrics/costs/month', description: 'Current month costs', priority: 'high' },
      { method: 'GET', path: '/api/metrics/costs/daily', description: 'Daily breakdown', priority: 'medium' },
      { method: 'GET', path: '/api/metrics/costs/fixed', description: 'Fixed costs', priority: 'medium' },
      { method: 'PUT', path: '/api/metrics/costs/fixed/{name}', description: 'Update fixed cost', priority: 'low', param: 'name' },
      { method: 'GET', path: '/api/metrics/costs/by-project', description: 'Costs by project', priority: 'low' },
      { method: 'GET', path: '/api/metrics/costs/recent', description: 'Recent costs', priority: 'low' },
      { method: 'DELETE', path: '/api/metrics/reset', description: 'Reset metrics', priority: 'low', dangerous: true },
    ]
  },
  {
    id: 'cleanup',
    name: 'Cleanup & Deletion',

    description: 'Data deletion and cleanup (8 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/deep-clean/preview', description: 'Preview orphaned data', priority: 'high' },
      { method: 'POST', path: '/api/deep-clean', description: 'Deep clean (?confirm=true)', priority: 'high', dangerous: true },
      { method: 'DELETE', path: '/api/status/structured/table/{table_name}', description: 'Delete DuckDB table', priority: 'medium', param: 'table_name', dangerous: true },
      { method: 'DELETE', path: '/api/status/structured/{project_id}/{filename}', description: 'Delete structured file', priority: 'medium', param: 'project_id, filename', dangerous: true },
      { method: 'DELETE', path: '/api/status/documents/{filename}', description: 'Delete ChromaDB doc', priority: 'medium', param: 'filename', dangerous: true },
      { method: 'DELETE', path: '/api/status/references/{filename}', description: 'Delete reference', priority: 'medium', param: 'filename', dangerous: true },
      { method: 'DELETE', path: '/api/status/references', description: 'Delete all references', priority: 'low', dangerous: true },
      { method: 'DELETE', path: '/api/status/project/{project_id}/all', description: 'Delete ALL project data', priority: 'low', param: 'project_id', dangerous: true },
    ]
  },
  {
    id: 'admin',
    name: 'Admin & Learning',

    description: 'Admin operations and learning system (24 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/admin/registry/status', description: 'Registry status (orphans)', priority: 'high' },
      { method: 'POST', path: '/api/admin/registry/repair', description: 'Repair registry orphans', priority: 'high' },
      { method: 'POST', path: '/api/admin/registry/sync', description: 'Sync duckdb_tables', priority: 'medium' },
      { method: 'GET', path: '/api/admin/learning/queries', description: 'Learned queries', priority: 'medium' },
      { method: 'DELETE', path: '/api/admin/learning/queries/{query_id}', description: 'Delete query', priority: 'low', param: 'query_id', dangerous: true },
      { method: 'GET', path: '/api/admin/learning/preferences', description: 'User preferences', priority: 'low' },
      { method: 'DELETE', path: '/api/admin/learning/preferences/{pref_id}', description: 'Delete preference', priority: 'low', param: 'pref_id', dangerous: true },
      { method: 'GET', path: '/api/admin/learning/feedback', description: 'Feedback history', priority: 'low' },
      { method: 'DELETE', path: '/api/admin/learning/feedback/{feedback_id}', description: 'Delete feedback', priority: 'low', param: 'feedback_id', dangerous: true },
      { method: 'GET', path: '/api/admin/learning/clarifications', description: 'Clarification patterns', priority: 'low' },
      { method: 'DELETE', path: '/api/admin/learning/clarifications/{pattern_id}', description: 'Delete clarification', priority: 'low', param: 'pattern_id', dangerous: true },
      { method: 'GET', path: '/api/admin/learning/mappings', description: 'Column mappings', priority: 'low' },
      { method: 'POST', path: '/api/admin/learning/mappings', description: 'Add mapping', priority: 'low' },
      { method: 'DELETE', path: '/api/admin/learning/mappings/{mapping_id}', description: 'Delete mapping', priority: 'low', param: 'mapping_id', dangerous: true },
      { method: 'GET', path: '/api/admin/learning/stats/detailed', description: 'Detailed stats', priority: 'low' },
      { method: 'GET', path: '/api/admin/learning/export/{data_type}', description: 'Export learning', priority: 'low', param: 'data_type' },
      { method: 'DELETE', path: '/api/admin/learning/clear/{data_type}', description: 'Clear learning', priority: 'low', param: 'data_type', dangerous: true },
      { method: 'GET', path: '/api/admin/references', description: 'Admin references', priority: 'low' },
      { method: 'DELETE', path: '/api/admin/references/{filename}', description: 'Delete reference', priority: 'low', param: 'filename', dangerous: true },
      { method: 'DELETE', path: '/api/admin/references/clear/all', description: 'Clear all refs', priority: 'low', dangerous: true },
      { method: 'GET', path: '/api/admin/rules', description: 'Admin rules', priority: 'low' },
      { method: 'DELETE', path: '/api/admin/rules/clear', description: 'Clear rules', priority: 'low', dangerous: true },
      { method: 'DELETE', path: '/api/admin/force-delete-project/{project_id}', description: 'Force delete project', priority: 'low', param: 'project_id', dangerous: true },
      { method: 'DELETE', path: '/api/admin/force-delete-project-by-name/{project_name}', description: 'Force delete by name', priority: 'low', param: 'project_name', dangerous: true },
    ]
  },
  {
    id: 'auth',
    name: 'Authentication',

    description: 'User authentication (9 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/auth/me', description: 'Get current user', priority: 'high' },
      { method: 'GET', path: '/api/auth/permissions', description: 'Get my permissions', priority: 'high' },
      { method: 'GET', path: '/api/auth/users', description: 'List users', priority: 'medium' },
      { method: 'POST', path: '/api/auth/users', description: 'Create user', priority: 'medium' },
      { method: 'PATCH', path: '/api/auth/users/{user_id}', description: 'Update user', priority: 'low', param: 'user_id' },
      { method: 'DELETE', path: '/api/auth/users/{user_id}', description: 'Delete user', priority: 'low', param: 'user_id', dangerous: true },
      { method: 'GET', path: '/api/auth/roles', description: 'List roles', priority: 'low' },
      { method: 'GET', path: '/api/auth/role-permissions', description: 'Role permissions', priority: 'low' },
      { method: 'PATCH', path: '/api/auth/role-permissions', description: 'Update role perms', priority: 'low' },
    ]
  },
  {
    id: 'security',
    name: 'Security',

    description: 'Security scanning (14 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/security/config', description: 'Security config', priority: 'high' },
      { method: 'PATCH', path: '/api/security/config', description: 'Update config', priority: 'medium' },
      { method: 'POST', path: '/api/security/scan', description: 'Force scan', priority: 'medium' },
      { method: 'GET', path: '/api/security/threats', description: 'Detected threats', priority: 'medium' },
      { method: 'GET', path: '/api/security/threats/summary', description: 'Threats summary', priority: 'medium' },
      { method: 'GET', path: '/api/security/audit/recent', description: 'Recent audit logs', priority: 'medium' },
      { method: 'GET', path: '/api/security/audit/summary', description: 'Audit summary', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/audit-logging', description: 'Toggle audit', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/input-validation', description: 'Toggle validation', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/pii-scan-llm', description: 'Toggle PII (LLM)', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/pii-scan-uploads', description: 'Toggle PII (uploads)', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/prompt-sanitization', description: 'Toggle sanitization', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/rate-limiting', description: 'Toggle rate limit', priority: 'low' },
      { method: 'POST', path: '/api/security/toggle/security-headers', description: 'Toggle headers', priority: 'low' },
    ]
  },
  {
    id: 'advisor',
    name: 'Advisor',

    description: 'HCM advisor (3 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/advisor/features', description: 'Advisor features', priority: 'high' },
      { method: 'POST', path: '/api/advisor/chat', description: 'Advisor chat', priority: 'high' },
      { method: 'POST', path: '/api/advisor/generate-playbook', description: 'Generate playbook', priority: 'medium' },
    ]
  },
  {
    id: 'connections',
    name: 'External Connections',

    description: 'External system connections (11 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/connections/{project_name}', description: 'List connections', priority: 'medium', param: 'project_name' },
      { method: 'POST', path: '/api/connections', description: 'Create connection', priority: 'medium' },
      { method: 'GET', path: '/api/connections/detail/{connection_id}', description: 'Get connection', priority: 'medium', param: 'connection_id' },
      { method: 'PUT', path: '/api/connections/{connection_id}', description: 'Update connection', priority: 'low', param: 'connection_id' },
      { method: 'DELETE', path: '/api/connections/{connection_id}', description: 'Delete connection', priority: 'low', param: 'connection_id', dangerous: true },
      { method: 'POST', path: '/api/connections/{connection_id}/test', description: 'Test connection', priority: 'medium', param: 'connection_id' },
      { method: 'GET', path: '/api/connections/{connection_id}/reports', description: 'List reports', priority: 'medium', param: 'connection_id' },
      { method: 'GET', path: '/api/connections/{connection_id}/reports/parameters', description: 'Report params', priority: 'low', param: 'connection_id' },
      { method: 'POST', path: '/api/connections/{connection_id}/execute', description: 'Execute report', priority: 'medium', param: 'connection_id' },
      { method: 'POST', path: '/api/connections/{connection_id}/reports/save', description: 'Save report', priority: 'low', param: 'connection_id' },
      { method: 'GET', path: '/api/connections/{connection_id}/reports/saved', description: 'Saved reports', priority: 'low', param: 'connection_id' },
    ]
  },
  {
    id: 'register',
    name: 'Register Extractor',

    description: 'Payroll register extraction (9 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/register/health', description: 'Extractor health', priority: 'high' },
      { method: 'GET', path: '/api/register/status', description: 'Extractor status', priority: 'medium' },
      { method: 'POST', path: '/api/register/upload', description: 'Upload register', priority: 'high' },
      { method: 'POST', path: '/api/register/extract', description: 'Extract data', priority: 'high' },
      { method: 'GET', path: '/api/register/extracts', description: 'List extractions', priority: 'medium' },
      { method: 'GET', path: '/api/register/extract/{extract_id}', description: 'Get extraction', priority: 'medium', param: 'extract_id' },
      { method: 'GET', path: '/api/register/extract/{extract_id}/raw', description: 'Get raw text', priority: 'low', param: 'extract_id' },
      { method: 'DELETE', path: '/api/register/extract/{extract_id}', description: 'Delete extraction', priority: 'low', param: 'extract_id', dangerous: true },
      { method: 'GET', path: '/api/register/job/{job_id}', description: 'Job status', priority: 'medium', param: 'job_id' },
    ]
  },
  {
    id: 'vacuum',
    name: 'Vacuum (Alias)',

    description: 'Vacuum endpoints (7 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/vacuum/health', description: 'Vacuum health', priority: 'medium' },
      { method: 'GET', path: '/api/vacuum/status', description: 'Vacuum status', priority: 'medium' },
      { method: 'POST', path: '/api/vacuum/upload', description: 'Vacuum upload', priority: 'medium' },
      { method: 'GET', path: '/api/vacuum/extracts', description: 'List extracts', priority: 'low' },
      { method: 'GET', path: '/api/vacuum/extract/{extract_id}', description: 'Get extract', priority: 'low', param: 'extract_id' },
      { method: 'DELETE', path: '/api/vacuum/extract/{extract_id}', description: 'Delete extract', priority: 'low', param: 'extract_id', dangerous: true },
      { method: 'GET', path: '/api/vacuum/job/{job_id}', description: 'Job status', priority: 'low', param: 'job_id' },
    ]
  },
  {
    id: 'export',
    name: 'Export',

    description: 'Data export (3 endpoints)',
    endpoints: [
      { method: 'GET', path: '/api/export/formats', description: 'Export formats', priority: 'medium' },
      { method: 'POST', path: '/api/export/data', description: 'Export data', priority: 'medium' },
      { method: 'POST', path: '/api/export/comparison', description: 'Export comparison', priority: 'low' },
    ]
  },
];

// Component
export default function AdminEndpoints() {
  const [expandedCategory, setExpandedCategory] = useState('platform');
  const [copiedUrl, setCopiedUrl] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('all');

  const isDark = document.documentElement.classList.contains('dark') || 
                 window.matchMedia('(prefers-color-scheme: dark)').matches;

  const c = {
    background: isDark ? '#0a0a0a' : '#f8f9fa',
    cardBg: isDark ? '#141414' : '#ffffff',
    border: isDark ? '#262626' : '#e5e7eb',
    text: isDark ? '#f5f5f5' : '#1f2937',
    textMuted: isDark ? '#a3a3a3' : '#6b7280',
    primary: '#6366f1',
    accent: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setCopiedUrl(text);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  const getFullUrl = (path) => `${PRODUCTION_URL}${path}`;

  const getMethodBadge = (method) => {
    const colors = {
      GET: { bg: '#10b981', text: '#fff' },
      POST: { bg: '#3b82f6', text: '#fff' },
      PUT: { bg: '#f59e0b', text: '#000' },
      PATCH: { bg: '#8b5cf6', text: '#fff' },
      DELETE: { bg: '#ef4444', text: '#fff' },
    };
    const color = colors[method] || { bg: '#6b7280', text: '#fff' };
    return (
      <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: '0.7rem', fontWeight: 600, fontFamily: 'monospace', background: color.bg, color: color.text, minWidth: 55, display: 'inline-block', textAlign: 'center' }}>
        {method}
      </span>
    );
  };

  const getPriorityBadge = (priority) => {
    const colors = { high: c.accent, medium: c.warning, low: c.textMuted };
    return (
      <span style={{ padding: '2px 6px', borderRadius: 4, fontSize: '0.65rem', background: `${colors[priority]}20`, color: colors[priority], textTransform: 'uppercase' }}>
        {priority}
      </span>
    );
  };

  const filteredCategories = ENDPOINT_CATEGORIES.map(category => {
    const filteredEndpoints = category.endpoints.filter(endpoint => {
      const matchesSearch = !searchTerm || endpoint.path.toLowerCase().includes(searchTerm.toLowerCase()) || endpoint.description.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesPriority = priorityFilter === 'all' || endpoint.priority === priorityFilter;
      return matchesSearch && matchesPriority;
    });
    return { ...category, endpoints: filteredEndpoints };
  }).filter(category => category.endpoints.length > 0);

  const totalEndpoints = ENDPOINT_CATEGORIES.reduce((sum, cat) => sum + cat.endpoints.length, 0);
  const filteredTotal = filteredCategories.reduce((sum, cat) => sum + cat.endpoints.length, 0);

  return (
    <div style={{ minHeight: '100vh', background: c.background, padding: '1.5rem', color: c.text }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: c.primary, textDecoration: 'none', marginBottom: '1rem' }}>
          <ArrowLeft size={16} /> Back to Platform Settings
        </Link>
        <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Link2 size={24} color={c.primary} />
          API Endpoints Reference
        </h1>
        <p style={{ margin: '0.5rem 0 0', color: c.textMuted }}>Complete reference of all {totalEndpoints} API endpoints</p>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 250 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: c.textMuted }} />
          <input type="text" placeholder="Search endpoints..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} style={{ width: '100%', padding: '0.75rem 0.75rem 0.75rem 2.5rem', background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, color: c.text, fontSize: '0.9rem' }} />
        </div>
        <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} style={{ padding: '0.75rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, color: c.text, fontSize: '0.9rem' }}>
          <option value="all">All Priorities</option>
          <option value="high">High Priority</option>
          <option value="medium">Medium Priority</option>
          <option value="low">Low Priority</option>
        </select>
        <div style={{ padding: '0.75rem 1rem', background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 8, fontSize: '0.85rem', color: c.textMuted }}>
          Showing {filteredTotal} of {totalEndpoints}
        </div>
      </div>

      <div style={{ padding: '0.75rem 1rem', background: c.cardBg, borderRadius: 8, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', border: `1px solid ${c.border}` }}>
        <span style={{ color: c.textMuted, fontSize: '0.85rem' }}>Base URL:</span>
        <code style={{ flex: 1, fontSize: '0.85rem', color: c.primary, fontFamily: 'monospace' }}>{PRODUCTION_URL}</code>
        <button onClick={() => copyToClipboard(PRODUCTION_URL)} style={{ padding: '0.35rem 0.75rem', background: c.border, border: 'none', borderRadius: 4, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem', color: copiedUrl === PRODUCTION_URL ? c.accent : c.textMuted, fontSize: '0.75rem' }}>
          {copiedUrl === PRODUCTION_URL ? <Check size={14} /> : <Copy size={14} />} {copiedUrl === PRODUCTION_URL ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {filteredCategories.map(category => (
          <div key={category.id} style={{ background: c.cardBg, border: `1px solid ${c.border}`, borderRadius: 10, overflow: 'hidden' }}>
            <button onClick={() => setExpandedCategory(expandedCategory === category.id ? null : category.id)} style={{ width: '100%', padding: '1rem 1.25rem', background: c.background, border: 'none', borderBottom: expandedCategory === category.id ? `1px solid ${c.border}` : 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', textAlign: 'left' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                {CATEGORY_ICONS[category.id] && React.createElement(CATEGORY_ICONS[category.id], { size: 20, color: c.primary })}
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', color: c.text }}>{category.name}</div>
                  <div style={{ fontSize: '0.75rem', color: c.textMuted }}>{category.description}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ background: c.border, padding: '2px 8px', borderRadius: 10, fontSize: '0.75rem', color: c.textMuted }}>{category.endpoints.length}</span>
                <span style={{ transform: expandedCategory === category.id ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s', color: c.textMuted }}>▼</span>
              </div>
            </button>
            {expandedCategory === category.id && (
              <div style={{ padding: '0.5rem' }}>
                {category.endpoints.map((endpoint, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', borderRadius: 8, background: endpoint.dangerous ? `${c.danger}08` : 'transparent', borderLeft: endpoint.dangerous ? `3px solid ${c.danger}` : '3px solid transparent' }}>
                    {getMethodBadge(endpoint.method)}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <code style={{ fontSize: '0.8rem', color: c.text, fontFamily: 'monospace', wordBreak: 'break-all' }}>{endpoint.path}</code>
                      <div style={{ fontSize: '0.75rem', color: c.textMuted, marginTop: '0.15rem' }}>
                        {endpoint.description}
                        {endpoint.param && <span style={{ color: c.warning, marginLeft: '0.5rem' }}>(requires: {endpoint.param})</span>}
                      </div>
                    </div>
                    {getPriorityBadge(endpoint.priority)}
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      <button onClick={() => copyToClipboard(getFullUrl(endpoint.path))} title="Copy URL" style={{ padding: '0.35rem', background: c.border, border: 'none', borderRadius: 4, cursor: 'pointer', display: 'flex', alignItems: 'center', color: copiedUrl === getFullUrl(endpoint.path) ? c.accent : c.textMuted }}>
                        {copiedUrl === getFullUrl(endpoint.path) ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                      {endpoint.method === 'GET' && !endpoint.param && (
                        <a href={getFullUrl(endpoint.path)} target="_blank" rel="noopener noreferrer" title="Open" style={{ padding: '0.35rem', background: c.border, border: 'none', borderRadius: 4, cursor: 'pointer', display: 'flex', alignItems: 'center', color: c.textMuted, textDecoration: 'none' }}>
                          <ExternalLink size={14} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: '2rem', padding: '1rem', background: c.border, borderRadius: 8, fontSize: '0.8rem', color: c.textMuted, textAlign: 'center' }}>
        <strong>Note:</strong> DELETE and POST endpoints cannot be tested via browser link.
        <br />Last updated: January 3, 2026 • {totalEndpoints} total endpoints
      </div>
    </div>
  );
}
