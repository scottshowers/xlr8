/* Navigation Styles */
.nav {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  padding: 1.25rem 0;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 3px rgba(42, 52, 65, 0.04);
}

.nav-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  text-decoration: none;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: translateX(2px);
}

.logo-mark {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 2px 8px rgba(131, 177, 109, 0.25));
  transition: filter 0.3s ease;
}

.logo:hover .logo-mark {
  filter: drop-shadow(0 4px 12px rgba(131, 177, 109, 0.35));
}

.logo-text {
  font-family: var(--font-header);
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--grass-green);
  letter-spacing: -0.02em;
}

/* Nav Links */
.nav-links {
  display: flex;
  gap: 0.25rem;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-links li {
  margin: 0;
}

.nav-links a {
  color: var(--text-secondary);
  text-decoration: none;
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  transition: all 0.3s ease;
  position: relative;
  display: block;
}

.nav-links a.active,
.nav-links a[aria-current="page"] {
  color: var(--grass-green);
  background: linear-gradient(135deg, rgba(131, 177, 109, 0.1), rgba(147, 171, 217, 0.08));
}

.nav-links a.active::after,
.nav-links a[aria-current="page"]::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 20%;
  right: 20%;
  height: 2px;
  background: var(--grass-green);
  border-radius: 2px;
}

.nav-links a:hover:not(.active):not([aria-current="page"]) {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .nav-content {
    flex-direction: column;
    gap: 1rem;
  }

  .nav-links {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }

  .nav-links a {
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
  }

  .logo-text {
    font-size: 1.5rem;
  }

  .logo-mark {
    width: 44px;
    height: 44px;
  }
}

@media (max-width: 480px) {
  .logo-text {
    font-size: 1.35rem;
  }

  .logo-mark {
    width: 40px;
    height: 40px;
  }

  .nav-links a {
    font-size: 0.8rem;
    padding: 0.5rem 0.75rem;
  }
}
