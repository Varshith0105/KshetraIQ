"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";

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
  refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Authentication is transported exclusively in the HttpOnly session cookie.
  // Do not mirror bearer credentials into Web Storage where injected scripts can read them.
  const [token] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const apiUrl = getApiBaseUrl();

  const getAuthHeaders = (): HeadersInit => ({ "Content-Type": "application/json" });

  const refreshUser = async (): Promise<User | null> => {
    try {
      const res = await fetch(`${apiUrl}/api/v1/auth/me`, {
        method: "GET",
        headers: getAuthHeaders(),
        credentials: "include",
      });
      if (res.ok) {
        const data: User = await res.json();
        setUser(data);
        return data;
      }
      setUser(null);
      return null;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

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
    setUser(data.user);
    return data.user;
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
    setUser(data.user);
    return data.user;
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
    setUser(data.user);
    return data.user;
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
    try {
      await fetch(`${apiUrl}/api/v1/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
      });
    } catch {
      // Ignore network errors on logout
    } finally {
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
    };
  }
  return context;
}
