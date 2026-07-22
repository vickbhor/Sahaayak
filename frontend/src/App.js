import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { AuthProvider } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Consultation from './pages/Consultation';
import Reports from './pages/Reports';
import ReportDetail from './pages/ReportDetail';
import Medications from './pages/Medications';
import Support from './pages/Support';
import './App.css';

function AppLayout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-layout">
      {mobileOpen && <div className="sidebar-backdrop" onClick={() => setMobileOpen(false)} />}
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <button className="mobile-menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open menu">
        <Menu size={20} />
      </button>
      <main className="main-content">{children}</main>
    </div>
  );
}

function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <AppLayout><Dashboard /></AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/consultation"
              element={
                <ProtectedRoute>
                  <AppLayout><Consultation /></AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <AppLayout><Reports /></AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports/:id"
              element={
                <ProtectedRoute>
                  <AppLayout><ReportDetail /></AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/medications"
              element={
                <ProtectedRoute>
                  <AppLayout><Medications /></AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/support"
              element={
                <ProtectedRoute>
                  <AppLayout><Support /></AppLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </Router>
      </AuthProvider>
    </LanguageProvider>
  );
}

export default App;
