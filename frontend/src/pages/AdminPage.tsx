import { PageHeader } from "@/components/common/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { UsersTab } from "@/components/admin/UsersTab";
import { VerticalsTab } from "@/components/admin/VerticalsTab";
import { StatusesTab } from "@/components/admin/StatusesTab";
import { BrandingTab } from "@/components/admin/BrandingTab";
import { SettingsTab } from "@/components/admin/SettingsTab";
import { ChatsTab } from "@/components/admin/ChatsTab";
import { PermissionsTab } from "@/components/admin/PermissionsTab";

export default function AdminPage() {
  return (
    <div>
      <PageHeader title="Admin Panel" description="Manage users, business verticals, project statuses, branding, access and application settings." />
      <Tabs defaultValue="users">
        <TabsList>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="verticals">Verticals</TabsTrigger>
          <TabsTrigger value="statuses">Statuses</TabsTrigger>
          <TabsTrigger value="branding">Branding</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="permissions">Access</TabsTrigger>
          <TabsTrigger value="chats">Assistant chats</TabsTrigger>
        </TabsList>
        <TabsContent value="users">
          <UsersTab />
        </TabsContent>
        <TabsContent value="verticals">
          <VerticalsTab />
        </TabsContent>
        <TabsContent value="statuses">
          <StatusesTab />
        </TabsContent>
        <TabsContent value="branding">
          <BrandingTab />
        </TabsContent>
        <TabsContent value="settings">
          <SettingsTab />
        </TabsContent>
        <TabsContent value="permissions">
          <PermissionsTab />
        </TabsContent>
        <TabsContent value="chats">
          <ChatsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
