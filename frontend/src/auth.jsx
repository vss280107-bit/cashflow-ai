import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, getToken, setToken } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!getToken());

  const refresh = useCallback(async () => {
    try {
      setUser(await api.me());
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (getToken()) refresh();
  }, [refresh]);

  const signIn = async (mode, form) => {
    const { access_token } = await (mode === "register" ? api.register(form) : api.login(form));
    setToken(access_token);
    await refresh();
  };
  const signOut = () => {
    setToken(null);
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, signIn, signOut, refresh }}>{children}</Ctx.Provider>;
}
