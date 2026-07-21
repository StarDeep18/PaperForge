import React, { createContext, useContext, useEffect, useState } from "react";
import {
  User as FirebaseUser,
  signInWithEmailAndPassword,
  signOut,
  createUserWithEmailAndPassword,
  updateProfile,
  onIdTokenChanged,
} from "firebase/auth";
import { auth } from "../services/firebase";
import axios from "axios";

interface UserProfile {
  id: string;
  email: string;
  display_name: string;
}

interface AuthContextType {
  currentUser: FirebaseUser | null;
  userProfile: UserProfile | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<FirebaseUser | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen to authentication token changes (handles login, logout, and token refreshes)
    const unsubscribe = onIdTokenChanged(auth, async (user) => {
      if (user) {
        setCurrentUser(user);
        
        // Sync user with backend
        try {
          const token = await user.getIdToken();
          // Store token in memory or Axios defaults headers for subsequent calls
          axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
          
          const response = await axios.post("/api/v1/auth/sync");
          setUserProfile(response.data);
          
          // Load workspace settings
          const { useWorkspaceSettings } = await import("../hooks/useWorkspaceSettings");
          await useWorkspaceSettings.getState().fetchSettings();
        } catch (error) {
          console.error("Failed to sync authenticated user with backend DB:", error);
          setUserProfile(null);
        }
      } else {
        setCurrentUser(null);
        setUserProfile(null);
        delete axios.defaults.headers.common["Authorization"];
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const login = async (email: string, pass: string) => {
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, pass);
    } catch (e) {
      setLoading(false);
      throw e;
    }
  };

  const register = async (email: string, pass: string, name: string) => {
    setLoading(true);
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, pass);
      await updateProfile(userCredential.user, { displayName: name });
      
      // Force trigger ID token refresh to load display name into token claims
      await userCredential.user.getIdToken(true);
    } catch (e) {
      setLoading(false);
      throw e;
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await signOut(auth);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ currentUser, userProfile, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
