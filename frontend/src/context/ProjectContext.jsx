/**
 * ProjectContext - DEPRECATED
 * 
 * This file re-exports from CustomerContext for backward compatibility.
 * All new code should import from CustomerContext directly.
 * 
 * MIGRATION: Replace imports of ProjectContext with CustomerContext
 */

export {
  CustomerContext as ProjectContext,
  CustomerContext as default,
  CustomerProvider as ProjectProvider,
  useCustomer as useProject,
  useRequireCustomer as useRequireProject,
} from './CustomerContext';
