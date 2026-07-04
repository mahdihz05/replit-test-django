import React, { createContext, useContext, useEffect, useState } from "react";
import { getToken, removeToken, setToken, apiFetch, getSelectedWorkspace, setSelectedWorkspace } from "./api";

interface User {
  id: string;
  phone_number: string;
  full_name?: string;
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
  createWorkspace: (name: string) => Promise<Workspace>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(getSelectedWorkspace());
  const [isLoading, setIsLoading] = useState(true);

  const refreshWorkspaces = async () => {
    try {
      const response = await apiFetch("/workspaces/");
      const list = Array.isArray(response) ? response : (response?.data ?? []);
      setWorkspaces(list);
      if (list.length === 0) {
        setSelectedWorkspaceId(null);
        setSelectedWorkspace(null);
      } else if (!selectedWorkspaceId || !list.find((w: Workspace) => w.id === selectedWorkspaceId)) {
        selectWorkspace(list[0].id);
      }
    } catch (error) {
      console.error("Failed to load workspaces", error);
    }
  };

  const createWorkspace = async (name: string): Promise<Workspace> => {
    const response = await apiFetch("/workspaces/", {
      method: "POST",
      data: { name },
    });
    const workspace = response?.data ?? response;
    setWorkspaces(prev => [...prev, workspace]);
    selectWorkspace(workspace.id);
    return workspace;
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const userData = await apiFetch("/auth/me/");
          setUser(userData?.data ?? userData);
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

  const selectedWorkspace = workspaces.find(w => w.id === selectedWorkspaceId) || null;

  const updateUser = (updatedUser: User) => {
    setUser(updatedUser);
  };

  return (
    <AuthContext.Provider value={{ user, workspaces, selectedWorkspace, isLoading, login, logout, selectWorkspace, refreshWorkspaces, createWorkspace, updateUser }}>
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
