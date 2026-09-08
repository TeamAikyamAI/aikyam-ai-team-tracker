export type Role = "admin" | "member" | "requestor";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  reports_to_id: number | null;
  vertical_id: number | null;
  external_manager_email: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CreateUserPayload {
  name: string;
  email: string;
  password: string;
  role: Role;
  reports_to_id?: number | null;
  vertical_id?: number | null;
  external_manager_email?: string | null;
}

export type UpdateUserPayload = Partial<Omit<CreateUserPayload, "password">> & {
  password?: string;
  is_active?: boolean;
};

export interface Vertical {
  id: number;
  name: string;
  head_name: string;
  head_email: string;
  is_active: boolean;
  created_at: string;
}

export interface CreateVerticalPayload {
  name: string;
  head_name: string;
  head_email: string;
}

export type UpdateVerticalPayload = Partial<CreateVerticalPayload> & { is_active?: boolean };

export interface Status {
  id: number;
  name: string;
  color: string;
  is_terminal: boolean;
  sort_order: number;
  is_active: boolean;
}

export interface CreateStatusPayload {
  name: string;
  color?: string;
  is_terminal?: boolean;
  sort_order?: number;
}

export type UpdateStatusPayload = Partial<CreateStatusPayload> & { is_active?: boolean };

export interface Project {
  id: number;
  name: string;
  description: string | null;
  vertical_id: number;
  status_id: number;
  created_by_id: number;
  source_request_id: number | null;
  /** Who in the business asked for it - usually a vertical head without a login. */
  assigned_by: string | null;
  assigned_on: string | null;
  remarks: string | null;
  target_date: string | null;
  actual_completion_date: string | null;
  created_at: string;
  updated_at: string;
  owner_ids: number[];
}

export interface CreateProjectPayload {
  name: string;
  description?: string;
  vertical_id: number;
  status_id: number;
  owner_ids: number[];
  assigned_by?: string | null;
  assigned_on?: string | null;
  remarks?: string | null;
  target_date?: string | null;
}

export type UpdateProjectPayload = Partial<CreateProjectPayload> & {
  actual_completion_date?: string | null;
};

export interface ProjectQueueItem {
  id: number;
  name: string;
  vertical_name: string;
  status_name: string;
  status_color: string;
}

export interface ProjectUpdate {
  id: number;
  project_id: number;
  author_id: number;
  plan: string | null;
  progress: string | null;
  problem: string | null;
  raw_bullets: string | null;
  created_at: string;
}

export interface CreateUpdatePayload {
  project_id: number;
  plan?: string;
  progress?: string;
  problem?: string;
  raw_bullets?: string;
}

export interface QuickFillPayload {
  bullets: string;
}

export interface QuickFillResult {
  plan: string;
  progress: string;
  problem: string;
}

export type RequestStatus = "submitted" | "under_review" | "approved" | "rejected" | "on_hold";

export interface ServiceRequest {
  id: number;
  vertical_id: number;
  requestor_id: number;
  title: string;
  description: string | null;
  /** Original upload name; the file itself comes from GET /requests/{id}/brd. */
  brd_filename: string | null;
  status: RequestStatus;
  reviewed_by_id: number | null;
  reviewed_at: string | null;
  review_notes: string | null;
  created_at: string;
}

export interface ReviewRequestPayload {
  decision: "approved" | "rejected" | "on_hold";
  review_notes?: string;
  status_id?: number;
  target_date?: string;
}

export interface AskPayload {
  question: string;
}

export interface AskResult {
  answer: string;
}

export interface AuditLog {
  id: number;
  user_id: number;
  user_name: string;
  action: string;
  entity_type: string;
  entity_id: number | null;
  details: string | null;
  created_at: string;
}

export interface AuditLogFilters {
  user_id?: number;
  action?: string;
  entity_type?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
}

export interface LogoMeta {
  has_custom: boolean;
  /** Cache-busting token (timestamp + content hash) that goes in the image URL. */
  version: string;
  url: string;
  content_type: string;
  filename: string;
  size_bytes: number;
}

export interface PublicSettings {
  app_name: string;
  org_name: string;
  login_footer: string;
  email_domain: string;
  chatbot_enabled: boolean;
  chatbot_name: string;
  chatbot_greeting: string;
  /** Newline-separated starter questions shown as chips. */
  chatbot_suggestions: string;
}

export interface SettingItem {
  key: string;
  group: string;
  label: string;
  type: "string" | "text" | "int" | "bool" | "select" | "secret";
  help: string;
  options: string[];
  min: number | null;
  max: number | null;
  value: string | number | boolean | null;
  /** For secrets: whether a value is already stored (the value itself never leaves the server). */
  is_set: boolean;
  /** Comes from backend/.env; shown read-only and rejected by the API if sent. */
  env_only: boolean;
}

export interface ChatMessage {
  id: number;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatAskResponse {
  session_id: string;
  answer: string;
}

export interface ChatConversation {
  session_id: string;
  user_id: number | null;
  user_name: string | null;
  started_at: string;
  last_at: string;
  message_count: number;
  first_question: string;
}

// --- permissions ------------------------------------------------------------

/** Feature keys the Admin grid can grant. Kept in step with backend REGISTRY. */
export type FeatureKey =
  | "dashboard"
  | "queue"
  | "apply"
  | "my_requests"
  | "requests_review"
  | "ask"
  | "my_day"
  | "team_day"
  | "projects_manage"
  | "projects_delete"
  | "projects_export"
  | "project_remarks"
  | "admin_panel"
  | "audit_trail";

export interface MyFeatures {
  role: Role;
  features: FeatureKey[];
}

export interface PermissionCell {
  allowed: boolean;
  /** Locked pairs can never be switched off - e.g. an admin's Admin Panel. */
  locked: boolean;
}

export interface PermissionFeature {
  key: FeatureKey;
  label: string;
  group: string;
  help: string;
  roles: Record<string, PermissionCell>;
}

export interface PermissionMatrix {
  roles: { key: string; label: string }[];
  features: PermissionFeature[];
}

// --- My Day -----------------------------------------------------------------

export interface DailyTask {
  id: number;
  user_id: number;
  title: string;
  task_date: string;
  completed_at: string | null;
  completed_on: string | null;
  sort_order: number;
  /** 0 = planned for this day; 3 = has been rolling over for three days. */
  carried_days: number;
}

export interface DaySummary {
  done: number;
  pending: number;
  carried: number;
}

export interface DayView {
  date: string;
  user_id: number;
  user_name: string;
  is_own: boolean;
  open: DailyTask[];
  done: DailyTask[];
  summary: DaySummary;
}

export interface TeamDayView {
  date: string;
  rows: { user_id: number; user_name: string; summary: DaySummary }[];
}

export interface UserBrief {
  id: number;
  name: string;
}
