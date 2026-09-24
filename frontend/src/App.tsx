import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { Toaster } from "@/components/ui/sonner";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { FeatureRoute } from "@/routes/FeatureRoute";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";
import { BrandSync } from "@/components/common/BrandSync";

import LoginPage from "@/pages/LoginPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import DashboardPage from "@/pages/DashboardPage";
import QueuePage from "@/pages/QueuePage";
import ApplyForServicePage from "@/pages/ApplyForServicePage";
import MyRequestsPage from "@/pages/MyRequestsPage";
import RequestsReviewPage from "@/pages/RequestsReviewPage";
import ProjectDetailPage from "@/pages/ProjectDetailPage";
import MyDayPage from "@/pages/MyDayPage";
import AskTrackerPage from "@/pages/AskTrackerPage";
import ApiKeysPage from "@/pages/ApiKeysPage";
import AdminPage from "@/pages/AdminPage";
import AuditTrailPage from "@/pages/AuditTrailPage";
import NotFoundPage from "@/pages/NotFoundPage";

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrandSync />
        <BrowserRouter>
          <AuthProvider>
            <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />

              {/* Every screen below is gated on the Admin access grid, never on
                  a role written into the code, so access can be changed from
                  the Admin panel without a rebuild. */}
              <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                  <Route element={<FeatureRoute features={["dashboard"]} />}>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/projects/:id" element={<ProjectDetailPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["queue"]} />}>
                    <Route path="/queue" element={<QueuePage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["apply"]} />}>
                    <Route path="/apply" element={<ApplyForServicePage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["my_requests"]} />}>
                    <Route path="/my-requests" element={<MyRequestsPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["requests_review"]} />}>
                    <Route path="/requests" element={<RequestsReviewPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["my_day", "team_day"]} />}>
                    <Route path="/my-day" element={<MyDayPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["ask"]} />}>
                    <Route path="/ask" element={<AskTrackerPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["api_keys"]} />}>
                    <Route path="/api-keys" element={<ApiKeysPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["admin_panel"]} />}>
                    <Route path="/admin" element={<AdminPage />} />
                  </Route>

                  <Route element={<FeatureRoute features={["audit_trail"]} />}>
                    <Route path="/audit" element={<AuditTrailPage />} />
                  </Route>

                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Route>

            </Routes>
            </ErrorBoundary>
          </AuthProvider>
        </BrowserRouter>
        <Toaster />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
