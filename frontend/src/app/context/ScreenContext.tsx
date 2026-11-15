"use client";

import React, { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef, ReactNode } from "react";

export interface ScreenContextData {
  screenId: string;
  screenTitle?: string;
  route?: string;
  selectedCrop?: string;
  filters?: Record<string, any>;
  displayedData?: Record<string, any>;
  activeTab?: string;
}

export interface UserActivityPayload {
  action: string;
  entity_type?: string;
  entity_id?: string;
  metadata?: Record<string, any>;
}

export interface ScreenContextType {
  screenContext: ScreenContextData;
  setScreenContext: (context: Partial<ScreenContextData>) => void;
  registerScreen: (screenId: string, screenTitle?: string, displayedData?: Record<string, any>, selectedCrop?: string) => void;
  updateDisplayedData: (data: Record<string, any>) => void;
  setSelectedCrop: (crop: string) => void;
  updateFilters: (filters: Record<string, any>) => void;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  logActivity: (activity: UserActivityPayload) => Promise<void>;
}

function isDeepEqual(objA: any, objB: any): boolean {
  if (objA === objB) return true;
  if (!objA || !objB) return objA === objB;
  if (typeof objA !== "object" || typeof objB !== "object") return false;

  const keysA = Object.keys(objA).filter((k) => objA[k] !== undefined);
  const keysB = Object.keys(objB).filter((k) => objB[k] !== undefined);
  if (keysA.length !== keysB.length) return false;

  for (const key of keysA) {
    if (!isDeepEqual(objA[key], objB[key])) return false;
  }
  return true;
}

const defaultContext: ScreenContextData = {
  screenId: "dashboard",
  screenTitle: "Farm Dashboard",
  displayedData: {},
  filters: {},
};

const ScreenContext = createContext<ScreenContextType | undefined>(undefined);

export function ScreenContextProvider({ children }: { children: ReactNode }) {
  const [screenContext, setContextState] = useState<ScreenContextData>(defaultContext);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  const setScreenContext = useCallback((updates: Partial<ScreenContextData>) => {
    setContextState((prev) => {
      const mergedData = updates.displayedData
        ? { ...(prev.displayedData || {}), ...updates.displayedData }
        : prev.displayedData;
      const mergedFilters = updates.filters
        ? { ...(prev.filters || {}), ...updates.filters }
        : prev.filters;
      const next: ScreenContextData = {
        ...prev,
        ...updates,
        displayedData: mergedData,
        filters: mergedFilters,
      };
      if (
        prev.screenId === next.screenId &&
        prev.screenTitle === next.screenTitle &&
        prev.selectedCrop === next.selectedCrop &&
        prev.activeTab === next.activeTab &&
        prev.route === next.route &&
        isDeepEqual(prev.displayedData, next.displayedData) &&
        isDeepEqual(prev.filters, next.filters)
      ) {
        return prev;
      }
      return next;
    });
  }, []);

  const registerScreen = useCallback(
    (screenId: string, screenTitle?: string, displayedData?: Record<string, any>, selectedCrop?: string) => {
      const resolvedTitle = screenTitle || screenId;
      setContextState((prev) => {
        const cropMatch = selectedCrop !== undefined ? prev.selectedCrop === selectedCrop : true;
        if (
          prev.screenId === screenId &&
          prev.screenTitle === resolvedTitle &&
          cropMatch &&
          isDeepEqual(prev.displayedData, displayedData || {})
        ) {
          return prev;
        }
        return {
          ...prev,
          screenId,
          screenTitle: resolvedTitle,
          displayedData: displayedData || {},
          ...(selectedCrop !== undefined ? { selectedCrop } : {}),
        };
      });
    },
    []
  );

  const updateDisplayedData = useCallback((data: Record<string, any>) => {
    setContextState((prev) => {
      const merged = { ...(prev.displayedData || {}), ...data };
      if (isDeepEqual(prev.displayedData, merged)) return prev;
      return {
        ...prev,
        displayedData: merged,
      };
    });
  }, []);

  const setSelectedCrop = useCallback((crop: string) => {
    setContextState((prev) => {
      if (prev.selectedCrop === crop) return prev;
      return {
        ...prev,
        selectedCrop: crop,
      };
    });
  }, []);

  const updateFilters = useCallback((filters: Record<string, any>) => {
    setContextState((prev) => {
      const merged = { ...(prev.filters || {}), ...filters };
      if (isDeepEqual(prev.filters, merged)) return prev;
      return {
        ...prev,
        filters: merged,
      };
    });
  }, []);

  const logActivity = useCallback(async (activity: UserActivityPayload) => {
    try {
      const baseUrl =
        process.env.NEXT_PUBLIC_API_URL ||
        (typeof window !== "undefined" && window.location
          ? `${window.location.protocol}//${window.location.hostname}:8000`
          : "http://localhost:8000");

      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("kshetraiq_session_token") || sessionStorage.getItem("kshetraiq_session_token")
          : null;

      await fetch(`${baseUrl}/api/v1/user/activities`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          ...activity,
          metadata: { screen_id: activity.metadata?.screen_id, ...activity.metadata },
        }),
      });
    } catch {
      // Non-blocking activity logging
    }
  }, []);

  const contextValue = useMemo<ScreenContextType>(
    () => ({
      screenContext,
      setScreenContext,
      registerScreen,
      updateDisplayedData,
      setSelectedCrop,
      updateFilters,
      activeConversationId,
      setActiveConversationId,
      logActivity,
    }),
    [
      screenContext,
      setScreenContext,
      registerScreen,
      updateDisplayedData,
      setSelectedCrop,
      updateFilters,
      activeConversationId,
      setActiveConversationId,
      logActivity,
    ]
  );

  return (
    <ScreenContext.Provider value={contextValue}>
      {children}
    </ScreenContext.Provider>
  );
}

export function useScreenContext(): ScreenContextType {
  const context = useContext(ScreenContext);
  if (!context) {
    throw new Error("useScreenContext must be used within a ScreenContextProvider");
  }
  return context;
}

/**
 * Convenience hook for screen components to register their context on mount & update.
 */
export function useRegisterScreenContext(
  screenId: string,
  screenTitle?: string,
  displayedData?: Record<string, any>,
  selectedCrop?: string
) {
  const { registerScreen } = useScreenContext();
  const lastSerialized = useRef<string>("");

  useEffect(() => {
    const serialized = JSON.stringify({ screenId, screenTitle, displayedData, selectedCrop });
    if (lastSerialized.current === serialized) return;
    lastSerialized.current = serialized;
    registerScreen(screenId, screenTitle, displayedData, selectedCrop);
  }, [screenId, screenTitle, displayedData, selectedCrop, registerScreen]);
}
