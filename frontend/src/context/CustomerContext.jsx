/**
 * CustomerContext - Global Customer State Management
 * 
 * Select a customer ONCE, it flows everywhere.
 * Persists to localStorage for session continuity.
 * 
 * IMPORTANT: customer.id (UUID) is the ONLY identifier used for:
 * - DuckDB table naming
 * - API calls
 * - All data operations
 * 
 * customer.name is for DISPLAY ONLY.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const CustomerContext = createContext(null);

export function CustomerProvider({ children }) {
  // Active customer state
  const [activeCustomer, setActiveCustomer] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load customers from API
  const loadCustomers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/customers/list');
      
      let customersArray = [];
      if (Array.isArray(response.data)) {
        customersArray = response.data;
      } else if (response.data?.customers) {
        customersArray = response.data.customers;
      }
      
      setCustomers(customersArray);
      setError(null);
      
      // Restore active customer from localStorage if valid
      const savedCustomerId = localStorage.getItem('xlr8_active_customer');
      if (savedCustomerId) {
        const savedCustomer = customersArray.find(c => c.id === savedCustomerId);
        if (savedCustomer) {
          setActiveCustomer(savedCustomer);
        }
      }
      
    } catch (err) {
      console.error('Failed to load customers:', err);
      setError('Failed to load customers');
      setCustomers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  // Select a customer
  const selectCustomer = useCallback((customer) => {
    setActiveCustomer(customer);
    if (customer) {
      localStorage.setItem('xlr8_active_customer', customer.id);
    } else {
      localStorage.removeItem('xlr8_active_customer');
    }
  }, []);

  // Clear active customer
  const clearCustomer = useCallback(() => {
    setActiveCustomer(null);
    localStorage.removeItem('xlr8_active_customer');
  }, []);

  // Refresh customers (after create/update/delete)
  const refreshCustomers = useCallback(async () => {
    await loadCustomers();
  }, [loadCustomers]);

  // Create a new customer
  const createCustomer = useCallback(async (customerData) => {
    try {
      const response = await api.post('/customers/create', customerData);
      await refreshCustomers();
      
      // Auto-select the new customer
      if (response.data?.customer) {
        selectCustomer(response.data.customer);
      }
      
      return response.data;
    } catch (err) {
      console.error('Failed to create customer:', err);
      throw err;
    }
  }, [refreshCustomers, selectCustomer]);

  // Update a customer
  const updateCustomer = useCallback(async (customerId, updates) => {
    try {
      const response = await api.put(`/customers/${customerId}`, updates);
      await refreshCustomers();
      
      // Update active customer if it was the one updated
      if (activeCustomer?.id === customerId && response.data?.customer) {
        setActiveCustomer(response.data.customer);
      }
      
      return response.data;
    } catch (err) {
      console.error('Failed to update customer:', err);
      throw err;
    }
  }, [refreshCustomers, activeCustomer]);

  // Delete a customer
  const deleteCustomer = useCallback(async (customerId) => {
    try {
      await api.delete(`/customers/${customerId}`);
      await refreshCustomers();
      
      // Clear active customer if it was deleted
      if (activeCustomer?.id === customerId) {
        clearCustomer();
      }
      
      return true;
    } catch (err) {
      console.error('Failed to delete customer:', err);
      throw err;
    }
  }, [refreshCustomers, activeCustomer, clearCustomer]);

  const value = {
    // State
    activeCustomer,
    customers,
    loading,
    error,
    
    // Actions
    selectCustomer,
    clearCustomer,
    refreshCustomers,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    
    // Computed - customer.id is the ONLY identifier
    hasActiveCustomer: !!activeCustomer,
    customerId: activeCustomer?.id || null,      // THE identifier for all operations
    customerName: activeCustomer?.name || null,  // Display only
    
    // DEPRECATED aliases for backward compatibility during migration
    activeProject: activeCustomer,
    projects: customers,
    selectProject: selectCustomer,
    clearProject: clearCustomer,
    refreshProjects: refreshCustomers,
    createProject: createCustomer,
    updateProject: updateCustomer,
    deleteProject: deleteCustomer,
    hasActiveProject: !!activeCustomer,
    projectId: activeCustomer?.id || null,
    projectName: activeCustomer?.name || null,
    projectCode: activeCustomer?.id || null,  // Maps to id now, not a separate code
  };

  return (
    <CustomerContext.Provider value={value}>
      {children}
    </CustomerContext.Provider>
  );
}

// Hook to use customer context
export function useCustomer() {
  const context = useContext(CustomerContext);
  if (!context) {
    throw new Error('useCustomer must be used within a CustomerProvider');
  }
  return context;
}

// Hook that requires an active customer (shows selector if none)
export function useRequireCustomer() {
  const context = useCustomer();
  return {
    ...context,
    isReady: context.hasActiveCustomer && !context.loading,
    needsCustomer: !context.hasActiveCustomer && !context.loading,
  };
}

// DEPRECATED: Backward compatibility aliases
export const ProjectContext = CustomerContext;
export const ProjectProvider = CustomerProvider;
export const useProject = useCustomer;
export const useRequireProject = useRequireCustomer;

export default CustomerContext;
