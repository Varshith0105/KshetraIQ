"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";

export interface User {
  user_id: string;
  email: string;
  full_name: string;
  created_at: string;
  auth_provider?: string;
  phone_number?: string | null;
  avatar_url?: string | null;
}

export interface SendOtpResult {
  status: string;
  phone_number: string;
  message: string;
  expires_in_seconds: number;
  provider_configured: boolean;
  dev_otp?: string | null;
}

export const TOKEN_STORAGE_KEY = "kshetraiq_session_token";
export const USER_STORAGE_KEY = "kshetraiq_session_user";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY) || sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY) || sessionStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(token: string, user: User, rememberMe: boolean): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);

    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem(TOKEN_STORAGE_KEY, token);
    storage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // Gracefully handle private browsing or storage quota restrictions
  }
}

export function clearStoredSession(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Ignore
  }
}

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined" && window.location) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  token: string | null;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<User>;
  register: (email: string, password: string, fullName: string, confirmPassword?: string, rememberMe?: boolean) => Promise<User>;
  sendOtp: (phoneNumber: string) => Promise<SendOtpResult>;
  verifyOtp: (phoneNumber: string, otp: string, fullName?: string) => Promise<User>;
  getGoogleAuthUrl: (redirectUri?: string) => Promise<{ configured: boolean; url: string; message?: string }>;
  logout: () => Promise<void>;
  refreshUser: (tokenOverride?: string) => Promise<User | null>;
  handleAuthSuccess: (data: { token?: string; user?: User; [key: string]: any }, rememberMe?: boolean) => User;
  getAuthHeaders: (extra?: HeadersInit) => HeadersInit;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => getStoredUser());
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [loading, setLoading] = useState<boolean>(() => {
    if (typeof window === "undefined") return true;
    return !getStoredToken() && !getStoredUser();
  });

  const apiUrl = getApiBaseUrl();

  const getAuthHeaders = useCallback((extra?: HeadersInit): HeadersInit => {
    const currentToken = token || getStoredToken();
    return {
      "Content-Type": "application/json",
      ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
      ...extra,
    };
  }, [token]);

  const handleAuthSuccess = useCallback((data: { token?: string; user?: User; [key: string]: any }, rememberMe = false): User => {
    const incomingUser: User = data.user || {
      user_id: data.user_id || "",
      email: data.email || "",
      full_name: data.display_name || data.full_name || "",
      created_at: data.created_at || new Date().toISOString(),
      auth_provider: data.auth_provider || "email",
      avatar_url: data.avatar_url || null,
      phone_number: data.phone_number || null,
    };
    const incomingToken = data.token || "";

    setUser(incomingUser);
    if (incomingToken) {
      setToken(incomingToken);
      setStoredSession(incomingToken, incomingUser, rememberMe || !!data.remember_me);
    }
    setLoading(false);
    return incomingUser;
  }, []);

  const refreshUser = useCallback(async (tokenOverride?: string): Promise<User | null> => {
    const effectiveToken = tokenOverride || token || getStoredToken();
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (effectiveToken) {
        headers["Authorization"] = `Bearer ${effectiveToken}`;
      }
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);
      const res = await fetch(`${apiUrl}/api/v1/auth/me`, {
        method: "GET",
        headers,
        credentials: "include",
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data: User = await res.json();
        setUser(data);
        if (effectiveToken) {
          setToken(effectiveToken);
          setStoredSession(effectiveToken, data, true);
        }
        return data;
      }
      // If 401 Unauthorized explicitly, session has expired
      if (res.status === 401) {
        clearStoredSession();
        setUser(null);
        setToken(null);
        return null;
      }
      return user || getStoredUser();
    } catch {
      // Network error, offline, or Render waking up: retain stored session so user is not logged out
      return user || getStoredUser();
    } finally {
      setLoading(false);
    }
  }, [apiUrl, token, user]);

  useEffect(() => {
    const storedToken = getStoredToken();
    const storedUser = getStoredUser();
    if (storedToken && !token) {
      setToken(storedToken);
    }
    if (storedUser && !user) {
      setUser(storedUser);
      setLoading(false);
    }
    refreshUser(storedToken || undefined);
  }, [refreshUser]);

  const login = async (email: string, password: string, rememberMe = false): Promise<User> => {
    const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email: email.trim(), password, remember_me: rememberMe }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || "Invalid email or password.");
    }

    const data = await res.json();
    return handleAuthSuccess(data, rememberMe);
  };

  const register = async (
    email: string,
    password: string,
    fullName: string,
    confirmPassword?: string,
    rememberMe = false
  ): Promise<User> => {
    const res = await fetch(`${apiUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        email: email.trim(),
        password,
        confirm_password: confirmPassword || password,
        full_name: fullName.trim(),
        remember_me: rememberMe,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || "Registration failed. Please check your details.");
    }

    const data = await res.json();
    return handleAuthSuccess(data, rememberMe);
  };

  const sendOtp = async (phoneNumber: string): Promise<SendOtpResult> => {
    const res = await fetch(`${apiUrl}/api/v1/auth/otp/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone_number: phoneNumber.trim() }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || "Failed to send OTP.");
    }

    return await res.json();
  };

  const verifyOtp = async (phoneNumber: string, otp: string, fullName?: string): Promise<User> => {
    const res = await fetch(`${apiUrl}/api/v1/auth/otp/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        phone_number: phoneNumber.trim(),
        otp: otp.trim(),
        full_name: fullName?.trim() || undefined,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || "OTP verification failed.");
    }

    const data = await res.json();
    return handleAuthSuccess(data, false);
  };

  const getGoogleAuthUrl = async (redirectUri?: string): Promise<{ configured: boolean; url: string; message?: string }> => {
    const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : "";
    const res = await fetch(`${apiUrl}/api/v1/auth/google/url${query}`, {
      method: "GET",
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || "Failed to get Google OAuth URL.");
    }

    return await res.json();
  };

  const logout = async (): Promise<void> => {
    const effectiveToken = token || getStoredToken();
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (effectiveToken) {
        headers["Authorization"] = `Bearer ${effectiveToken}`;
      }
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers,
        credentials: "include",
      });
    } catch {
      // Ignore network errors on logout
    } finally {
      clearStoredSession();
      setToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        token,
        login,
        register,
        sendOtp,
        verifyOtp,
        getGoogleAuthUrl,
        logout,
        refreshUser,
        handleAuthSuccess,
        getAuthHeaders,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    return {
      user: null,
      loading: true,
      token: null,
      login: async () => {
        throw new Error("AuthProvider not mounted");
      },
      register: async () => {
        throw new Error("AuthProvider not mounted");
      },
      sendOtp: async () => {
        throw new Error("AuthProvider not mounted");
      },
      verifyOtp: async () => {
        throw new Error("AuthProvider not mounted");
      },
      getGoogleAuthUrl: async (): Promise<{ configured: boolean; url: string; message?: string }> => ({ configured: false, url: "" }),
      logout: async () => {},
      refreshUser: async () => null,
      handleAuthSuccess: () => {
        throw new Error("AuthProvider not mounted");
      },
      getAuthHeaders: () => ({ "Content-Type": "application/json" }),
    };
  }
  return context;
}
