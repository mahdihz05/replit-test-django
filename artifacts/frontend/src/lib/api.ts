export const API_BASE_URL = "/api";

export function getToken() {
  return localStorage.getItem("access_token");
}

export function setToken(token: string) {
  localStorage.setItem("access_token", token);
}

export function removeToken() {
  localStorage.removeItem("access_token");
}

export function getSelectedWorkspace() {
  return localStorage.getItem("selected_workspace_id");
}

export function setSelectedWorkspace(id: string | null) {
  if (id) {
    localStorage.setItem("selected_workspace_id", id);
  } else {
    localStorage.removeItem("selected_workspace_id");
  }
}

interface FetchOptions extends RequestInit {
  data?: any;
}

export async function apiFetch(endpoint: string, options: FetchOptions = {}) {
  const { data, headers: customHeaders, ...rest } = options;
  const token = getToken();

  const headers = new Headers(customHeaders);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  // Only set JSON content type when body is not FormData
  const isFormData = data instanceof FormData;
  if (!isFormData) {
    headers.set("Content-Type", "application/json");
  }

  const config: RequestInit = {
    ...rest,
    headers,
  };

  if (data) {
    config.body = isFormData ? data : JSON.stringify(data);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

  if (!response.ok) {
    if (response.status === 401) {
      removeToken();
      window.location.href = "/login";
    }
    const errorData = await response.json().catch(() => ({}));
    const flattenError = (value: unknown): string => {
      if (typeof value === "string") return value;
      if (Array.isArray(value))
        return value.map(flattenError).filter(Boolean).join("، ");
      if (value && typeof value === "object") {
        return Object.entries(value)
          .map(([field, detail]) => `${field}: ${flattenError(detail)}`)
          .filter(Boolean)
          .join(" | ");
      }
      return "";
    };
    const message =
      flattenError(errorData.error || errorData.detail || errorData.message) ||
      `خطای سرور (${response.status})`;
    throw new Error(message);
  }

  // Some endpoints might return empty response
  if (response.status === 204) {
    return null;
  }

  return response.json();
}
