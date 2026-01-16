/**
 * AdminHub.jsx - Platform Settings
 * 
 * Simplified admin hub with only working/needed features.
 * 
 * Phase 4A UX Cleanup - January 2026
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, Permissions } from '../context/AuthContext';
import { 
  Settings, 
  Users, 
  Shield, 
  Lock, 
  Plug, 
  Trash2, 
  ChevronRight,
  Brain
} from 'lucide-react';

// ==================== ADMIN SECTIONS CONFIG ====================
const ADMIN_SECTIONS = [
  {
    id: 'platform-ops',
    title: 'Platform Operations',
    cards: [
      {
        id: 'intelligence',
        title: 'Intelligence Test',
        description: 'Test query resolution pipeline and SQL generation',
        icon: Brain,
        route: '/admin/intelligence-test',
        permission: Permissions.OPS_CENTER,
        color: '#8b5cf6',
      },
      {
        id: 'cleanup',
        title: 'Data Cleanup',
        description: 'Delete project data, tables, and documents',
        icon: Trash2,
        route: '/admin/data-cleanup',
        permission: Permissions.OPS_CENTER,
        color: '#ef4444',
      },
    ],
  },
  {
    id: 'users-security',
    title: 'Users & Security',
    cards: [
      {
        id: 'users',
        title: 'User Management',
        description: 'Create accounts, assign roles and projects',
        icon: Users,
        route: '/admin/settings?tab=users',
        permission: Permissions.USER_MANAGEMENT,
        color: '#0ea5e9',
      },
      {
        id: 'permissions',
        title: 'Role Permissions',
        description: 'Configure what each role can access',
        icon: Shield,
        route: '/admin/settings?tab=permissions',
        permission: Permissions.ROLE_PERMISSIONS,
        color: '#14b8a6',
      },
      {
        id: 'security',
        title: 'Security Settings',
        description: 'MFA, session management, audit logs',
        icon: Lock,
        route: '/admin/settings?tab=security',
        permission: Permissions.SECURITY_SETTINGS,
        color: '#f97316',
      },
    ],
  },
  {
    id: 'integrations',
    title: 'Integrations',
    cards: [
      {
        id: 'ukg',
        title: 'UKG Connections',
        description: 'Connect to UKG Pro, WFM, and Ready APIs',
        icon: Plug,
        route: '/admin/settings?tab=integrations',
        permission: Permissions.OPS_CENTER,
        color: '#ec4899',
      },
    ],
  },
];

// ==================== ADMIN CARD COMPONENT ====================
function AdminCard({ card, onClick }) {
  const Icon = card.icon;
  
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '16px',
        padding: '20px',
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        e.currentTarget.style.borderColor = card.color;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.borderColor = 'var(--border)';
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 'var(--radius-md)',
          background: `${card.color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Icon size={22} color={card.color} />
      </div>
      
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '4px',
          }}
        >
          <span style={{ 
            fontSize: 'var(--text-base)', 
            fontWeight: 600, 
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-body)'
          }}>
            {card.title}
          </span>
          <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
        </div>
        <div style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-muted)',
          lineHeight: 1.4,
        }}>
          {card.description}
        </div>
      </div>
    </button>
  );
}

// ==================== ADMIN SECTION COMPONENT ====================
function AdminSection({ section, visibleCards, onCardClick }) {
  if (visibleCards.length === 0) return null;
  
  return (
    <div style={{ marginBottom: '40px' }}>
      <h2 style={{
        fontSize: '18px',
        fontWeight: 600,
        color: 'var(--text-primary)',
        margin: '0 0 16px 0',
        fontFamily: "'Sora', var(--font-body)",
      }}>
        {section.title}
      </h2>
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '16px',
      }}>
        {visibleCards.map((card) => (
          <AdminCard
            key={card.id}
            card={card}
            onClick={() => onCardClick(card.route)}
          />
        ))}
      </div>
    </div>
  );
}

// ==================== MAIN COMPONENT ====================
export default function AdminHub() {
  const navigate = useNavigate();
  const { hasPermission, isAdmin } = useAuth();
  
  const handleCardClick = (route) => {
    navigate(route);
  };
  
  // Filter cards based on permissions
  const getVisibleCards = (cards) => {
    return cards.filter((card) => {
      if (!card.permission) return true;
      if (isAdmin) return true;
      return hasPermission(card.permission);
    });
  };
  
  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ 
          margin: 0, 
          fontSize: '20px', 
          fontWeight: 600, 
          color: 'var(--text-primary)', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '10px',
          fontFamily: "'Sora', var(--font-body)"
        }}>
          <div style={{ 
            width: '36px', 
            height: '36px', 
            borderRadius: '10px', 
            backgroundColor: 'var(--grass-green)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center' 
          }}>
            <Settings size={20} color="#ffffff" />
          </div>
          Platform Settings
        </h1>
      </div>

      {/* Sections */}
      {ADMIN_SECTIONS.map((section) => {
        const visibleCards = getVisibleCards(section.cards);
        return (
          <AdminSection
            key={section.id}
            section={section}
            visibleCards={visibleCards}
            onCardClick={handleCardClick}
          />
        );
      })}
    </div>
  );
}
