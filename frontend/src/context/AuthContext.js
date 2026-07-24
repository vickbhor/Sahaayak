import React, { createContext, useContext, useState, useEffect } from 'react';
import client from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('sahaayak_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('sahaayak_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const init = async () => {
      const storedToken = localStorage.getItem('sahaayak_token');
      if (storedToken) {
        try {
          const res = await client.get('/api/auth/me');
          setUser(res.data);
          localStorage.setItem('sahaayak_user', JSON.stringify(res.data));
        } catch (err) {
          localStorage.removeItem('sahaayak_token');
          localStorage.removeItem('sahaayak_user');
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  const login = async (email, password) => {
    const res = await client.post('/api/auth/login', { email, password });
    localStorage.setItem('sahaayak_token', res.data.token);
    localStorage.setItem('sahaayak_user', JSON.stringify(res.data.user));
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data.user;
  };

  const register = async (name, email, phone, password) => {
    const res = await client.post('/api/auth/register', { name, email, phone, password });
    localStorage.setItem('sahaayak_token', res.data.token);
    localStorage.setItem('sahaayak_user', JSON.stringify(res.data.user));
    setToken(res.data.token);
    setUser(res.data.user);
    return res.data.user;
  };

  const logout = () => {
    localStorage.removeItem('sahaayak_token');
    localStorage.removeItem('sahaayak_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
