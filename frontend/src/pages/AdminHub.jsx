/**
 * AdminHub.jsx - Admin Navigation Hub
 * 
 * Card-based entry point for all administrative functions.
 * Organizes admin tools into logical sections with clear navigation.
 * 
 * Created: January 14, 2026
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, Permissions } from '../context/AuthContext';
import { PageHeader } from '../components/ui';
import { 
  Settings, 
  BarChart3, 
  Users, 
  Shield, 
  Lock, 
  Plug, 
  Trash2, 
  Wrench,
  Zap,
  BookOpen,
  Library,
  FileText,
  ChevronRight,
  Activity,
  Database,
  Brain
} from 'lucide-react';

const COLORS = {
  primary: '#83b16d',
  text: '#1a2332',
  textSecondary: '#64748b',
  bg: '#f8fafc',
  card: '#ffffff',
  border: '#e2e8f0',
};

// ==================== ADMIN SECTIONS CONFIG ====================
const ADMIN_SECTIONS = [
  {
    id: 'platform-ops',
    title: 'Platform Operations',
    description: 'Monitor system health, test APIs, and manage data',
    cards: [
      {
        id: 'system',
        title: 'System Monitor',
        description: 'Database status, API health, performance metrics',
        icon: Activity,
        route: '/admin/settings?tab=system',
        permission: Permissions.OPS_CENTER,
        color: '#3b82f6',
      },
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
        id: 'endpoints',
        title: 'API Endpoints',
        description: 'Test and debug API endpoints directly',
        icon: Wrench,
        route: '/admin/endpoints',
        permission: Permissions.OPS_CENTER,
        color: '#06b6d4',
      },
      {
        id: 'cleanup',
        title: 'Data Cleanup',
        description: 'Delete tables, documents, or full system wipe',
        icon: Trash2,
        route: '/admin/data-cleanup',
        permission: Permissions.OPS_CENTER,
        color: '#ef4444',
      },
    ],
  },
  {
    id: 'content',
    title: 'Content Libraries',
    description: 'Manage standards, reference docs, and playbook templates',
    cards: [
      {
        id: 'standards',
        title: 'Standards Library',
        description: 'Compliance standards and regulatory requirements',
        icon: FileText,
        route: '/standards',
        permission: null,
        color: '#f59e0b',
      },
      {
        id: 'reference',
        title: 'Reference Library',
        description: 'Product documentation and best practices',
        icon: Library,
        route: '/reference-library',
        permission: null,
        color: '#10b981',
      },
      {
        id: 'playbook-builder',
        title: 'Playbook Builder',
        description: 'Create and manage playbook templates',
        icon: BookOpen,
        route: '/admin/playbook-builder',
        permission: null,
        color: '#6366f1',
      },
    ],
  },
  {
    id: 'users-security',
    title: 'Users & Security',
    description: 'Manage accounts, roles, and access controls',
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
      {
        id: 'personas',
        title: 'AI Personas',
        description: 'Configure AI personality and response styles',
        icon: Brain,
        route: '/admin/settings?tab=personas',
        permission: null,
        color: '#a855f7',
      },
    ],
  },
  {
    id: 'integrations',
    title: 'Integrations',
    description: 'Connect to external systems and APIs',
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
        gap: 16,
        padding: 20,
        background: COLORS.card,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 12,
        cursor: 'pointer',
        textAlign: 'left',
        width: '100%',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = card.color;
        e.currentTarget.style.boxShadow = `0 4px 12px ${card.color}15`;
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = COLORS.border;
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 10,
          background: `${card.color}12`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Icon size={24} color={card.color} />
      </div>
      
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: COLORS.text,
            marginBottom: 4,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {card.title}
          <ChevronRight size={16} color={COLORS.textSecondary} />
        </div>
        <div
          style={{
            fontSize: 13,
            color: COLORS.textSecondary,
            lineHeight: 1.4,
          }}
        >
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
    <div style={{ marginBottom: 40 }}>
      <div style={{ marginBottom: 16 }}>
        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: COLORS.text,
            margin: 0,
            fontFamily: "'Sora', sans-serif",
          }}
        >
          {section.title}
        </h2>
        <p
          style={{
            fontSize: 14,
            color: COLORS.textSecondary,
            margin: '4px 0 0 0',
          }}
        >
          {section.description}
        </p>
      </div>
      
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 16,
        }}
      >
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
      <PageHeader
        icon={Settings}
        title="Administration"
        subtitle="Platform settings, libraries, and system management"
      />
      
      <div style={{ maxWidth: 1200 }}>
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
      
      <div
        style={{
          marginTop: 24,
          padding: 20,
          background: COLORS.bg,
          borderRadius: 8,
          border: `1px solid ${COLORS.border}`,
        }}
      >
        <p
          style={{
            fontSize: 13,
            color: COLORS.textSecondary,
            margin: 0,
            lineHeight: 1.6,
          }}
        >
          <strong>Note:</strong> Some settings require administrator privileges.
          Contact your system administrator if you need access to restricted features.
        </p>
      </div>
    </div>
  );
}
