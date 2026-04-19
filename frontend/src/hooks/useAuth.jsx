import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { auth } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const token = auth.getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const u = await auth.me();
      setUser(u);
    } catch {
      auth.clearTokens();
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = async (email, password) => {
    const data = await auth.login(email, password);
    auth.setTokens(data.access, data.refresh);
    setUser(data.user);
    return data;
  };

  const logout = async () => {
    const refresh = localStorage.getItem("qw_refresh_token");
    try {
      await auth.logout(refresh);
    } catch {}
    auth.clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
