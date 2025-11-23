import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, FolderKanban, TrendingUp } from 'lucide-react';

export default function Navigation() {
  const location = useLocation();

  const links = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/projects', icon: FolderKanban, label: 'Projects' },
    { path: '/secure20', icon: TrendingUp, label: 'SECURE 2.0' },
  ];

  return (
    <nav className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur">
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center gap-1">
          {links.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                  isActive
                    ? 'border-cyan-500 text-cyan-400'
                    : 'border-transparent text-slate-400 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="text-sm font-medium">{link.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
