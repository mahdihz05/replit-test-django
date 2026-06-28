import React, { createContext, useContext, useEffect, useState } from "react";
import { getToken, removeToken, setToken, apiFetch, getSelectedWorkspace, setSelectedWorkspace } from "./api";

interface User {
  id: string;
  phone_number: string;
  first_name?: string;
  last_name?: string;
}

interface Workspace {
  id: string;
  name: string;
  owner: string;
  member_count: number;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  workspaces: Workspace[];
  selectedWorkspace: Workspace | null;
  isLoading: boolean;
  login: (token: string, userData: User) => void;
  logout: () => void;
  selectWorkspace: (id: string) => void;
  refreshWorkspaces: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(getSelectedWorkspace());
  const [isLoading, setIsLoading] = useState(true);

  const refreshWorkspaces = async () => {
    try {
      const data = await apiFetch("/workspaces/");
      setWorkspaces(data);
      if (data.length > 0 && !selectedWorkspaceId) {
        selectWorkspace(data[0].id);
      }
    } catch (error) {
      console.error("Failed to load workspaces", error);
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const userData = await apiFetch("/auth/me/");
          setUser(userData);
          await refreshWorkspaces();
        } catch (error) {
          removeToken();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = (token: string, userData: User) => {
    setToken(token);
    setUser(userData);
    refreshWorkspaces();
  };

  const logout = () => {
    removeToken();
    setUser(null);
    setWorkspaces([]);
    setSelectedWorkspaceId(null);
    localStorage.removeItem("selected_workspace_id");
  };

  const selectWorkspace = (id: string) => {
    setSelectedWorkspaceId(id);
    setSelectedWorkspace(id);
  };

  const selectedWorkspace = workspaces.find(w => w.id === selectedWorkspaceId) || workspaces[0] || null;

  return (
    <AuthContext.Provider value={{ user, workspaces, selectedWorkspace, isLoading, login, logout, selectWorkspace, refreshWorkspaces }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
