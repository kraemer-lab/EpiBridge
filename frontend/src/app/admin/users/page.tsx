"use client";

import { useEffect, useState } from "react";
import {
  User,
  UserCreate,
  UserUpdate,
  createUser,
  getUsers,
  updateUser,
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

const ROLE_OPTIONS = [
  {
    value: "researcher",
    label: "Researcher",
    description: "Prepare, validate and submit analyses.",
  },
  {
    value: "moderator",
    label: "Moderator",
    description: "Review submissions and outputs.",
  },
  {
    value: "maintainer",
    label: "Maintainer",
    description:
      "Create and manage institutional workspaces, resources and operational infrastructure.",
  },
  {
    value: "admin",
    label: "Administrator",
    description: "Manage users and institutional policy.",
  },
];

function roleLabel(value: string): string {
  return ROLE_OPTIONS.find((r) => r.value === value)?.label ?? value;
}

function RoleCheckboxes({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (roles: string[]) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
      {ROLE_OPTIONS.map((role) => {
        const checked = selected.includes(role.value);
        return (
          <label
            key={role.value}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "var(--spacing-sm)",
              cursor: "pointer",
              padding: "var(--spacing-xs) 0",
            }}
          >
            <input
              type="checkbox"
              checked={checked}
              onChange={() => {
                if (checked) {
                  onChange(selected.filter((r) => r !== role.value));
                } else {
                  onChange([...selected, role.value]);
                }
              }}
              style={{ marginTop: "2px" }}
            />
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                {role.label}
              </div>
              <div
                style={{
                  fontSize: "0.8rem",
                  color: "var(--color-text-secondary)",
                }}
              >
                {role.description}
              </div>
            </div>
          </label>
        );
      })}
    </div>
  );
}

function RoleBadges({ roles }: { roles: string[] }) {
  return (
    <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
      {(roles || []).map((r) => (
        <span
          key={r}
          style={{
            display: "inline-block",
            padding: "2px 8px",
            borderRadius: "4px",
            fontSize: "0.8rem",
            fontWeight: 600,
            background: "var(--color-surface, #f0f0f0)",
            color: "var(--color-text-secondary, #666)",
          }}
        >
          {roleLabel(r)}
        </span>
      ))}
    </div>
  );
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [capChangeWarning, setCapChangeWarning] = useState(false);

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [selectedRoles, setSelectedRoles] = useState<string[]>(["researcher"]);
  const [creating, setCreating] = useState(false);

  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editRoles, setEditRoles] = useState<string[]>([]);
  const [editAdvanced, setEditAdvanced] = useState<string[]>([]);
  const [editPassword, setEditPassword] = useState("");
  const [showPasswordReset, setShowPasswordReset] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    getUsers()
      .then(setUsers)
      .catch(() => setError("Failed to load users"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    if (!email.trim() || !displayName.trim() || !password.trim()) return;
    if (selectedRoles.length === 0) {
      setError("Select at least one role.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const data: UserCreate = {
        email: email.trim(),
        display_name: displayName.trim(),
        password,
        roles: selectedRoles,
      };
      await createUser(data);
      setEmail("");
      setDisplayName("");
      setPassword("");
      setSelectedRoles(["researcher"]);
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (u: User) => {
    setEditingUserId(u.id);
    setEditRoles(u.roles && u.roles.length > 0 ? u.roles : [u.role]);
    setEditAdvanced(u.capabilities.filter(c =>
      ["build.customize"].includes(c),
    ));
  };

  const cancelEdit = () => {
    setEditingUserId(null);
    setEditRoles([]);
    setEditAdvanced([]);
    setEditPassword("");
    setShowPasswordReset(false);
  };

  const saveEdit = async (userId: string) => {
    if (editRoles.length === 0) return;
    setSaving(true);
    setError(null);
    setCapChangeWarning(false);
    try {
      const data: UserUpdate = {
        roles: editRoles,
        advanced_capabilities: editAdvanced,
      };
      if (editPassword) {
        data.password = editPassword;
      }
      await updateUser(userId, data);
      setEditingUserId(null);
      setEditPassword("");
      setShowPasswordReset(false);
      if (currentUser && userId === currentUser.id) {
        setCapChangeWarning(true);
      }
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "var(--spacing-md)",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: 0 }}>
          Users
        </h2>
        <button
          className="btn"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? "Cancel" : "Create User"}
        </button>
      </div>

      {capChangeWarning && (
        <div
          className="card"
          style={{
            background: "#d1ecf1",
            color: "#0c5460",
            marginBottom: "var(--spacing-md)",
            padding: "var(--spacing-sm)",
          }}
        >
          Your capabilities have been updated. Please sign out and sign back in
          for the changes to take effect.
        </div>
      )}

      {error && (
        <div
          className="card"
          style={{
            background: "var(--color-error-bg, #fdecea)",
            color: "var(--color-error, #d32f2f)",
            marginBottom: "var(--spacing-md)",
            padding: "var(--spacing-sm)",
          }}
        >
          {error}
        </div>
      )}

      {showForm && (
        <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
          <div
            style={{
              display: "grid",
              gap: "var(--spacing-sm)",
              gridTemplateColumns: "1fr 1fr",
              marginBottom: "var(--spacing-md)",
            }}
          >
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  marginBottom: "4px",
                }}
              >
                Email
              </label>
              <input
                type="email"
                placeholder="user@institution.org"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  marginBottom: "4px",
                }}
              >
                Display Name
              </label>
              <input
                type="text"
                placeholder="Jane Researcher"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "0.85rem",
                  fontWeight: 500,
                  marginBottom: "4px",
                }}
              >
                Password
              </label>
              <input
                type="password"
                placeholder="Initial password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: "100%" }}
              />
            </div>
          </div>

          <label
            style={{
              display: "block",
              fontSize: "0.85rem",
              fontWeight: 500,
              marginBottom: "4px",
            }}
          >
            Roles
          </label>
          <RoleCheckboxes
            selected={selectedRoles}
            onChange={setSelectedRoles}
          />

          <div style={{ marginTop: "var(--spacing-md)" }}>
            <button
              className="btn btn-primary"
              onClick={handleCreate}
              disabled={
                creating ||
                !email.trim() ||
                !displayName.trim() ||
                !password.trim() ||
                selectedRoles.length === 0
              }
            >
              {creating ? "Creating..." : "Create User"}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : users.length === 0 ? (
        <div className="card empty-state">No users found.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Roles</th>
                <th>Capabilities</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 500 }}>{u.display_name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {u.email}
                  </td>
                  <td>
                    {editingUserId === u.id ? (
                      <div
                        style={{
                          display: "flex",
                          flexDirection: "column",
                          gap: "var(--spacing-xs)",
                        }}
                      >
                        <RoleCheckboxes
                          selected={editRoles}
                          onChange={setEditRoles}
                        />

                        <div
                          style={{
                            marginTop: "var(--spacing-sm)",
                            paddingTop: "var(--spacing-sm)",
                            borderTop: "1px solid var(--color-border)",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "0.75rem",
                              fontWeight: 600,
                              textTransform: "uppercase",
                              letterSpacing: "0.05em",
                              color: "var(--color-text-secondary)",
                              marginBottom: "var(--spacing-xs)",
                            }}
                          >
                            Advanced Permissions
                          </div>
                          <label
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "var(--spacing-sm)",
                              cursor: "pointer",
                              fontSize: "0.85rem",
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={editAdvanced.includes("build.customize")}
                              onChange={() => {
                                if (editAdvanced.includes("build.customize")) {
                                  setEditAdvanced(
                                    editAdvanced.filter(
                                      (c) => c !== "build.customize",
                                    ),
                                  );
                                } else {
                                  setEditAdvanced([
                                    ...editAdvanced,
                                    "build.customize",
                                  ]);
                                }
                              }}
                            />
                            <span>Custom Build Strategy</span>
                          </label>
                          <div
                            style={{
                              fontSize: "0.75rem",
                              color: "var(--color-text-secondary)",
                              marginLeft: "28px",
                            }}
                          >
                            Build custom Docker images from
                            user-provided Dockerfiles.
                          </div>
                        </div>

                        {!showPasswordReset ? (
                          <div style={{ marginTop: "var(--spacing-sm)" }}>
                            <button
                              className="btn btn-sm"
                              onClick={() => setShowPasswordReset(true)}
                            >
                              Reset Password
                            </button>
                          </div>
                        ) : (
                          <div
                            style={{
                              marginTop: "var(--spacing-sm)",
                              paddingTop: "var(--spacing-sm)",
                              borderTop: "1px solid var(--color-border)",
                            }}
                          >
                            <div
                              style={{
                                fontSize: "0.75rem",
                                fontWeight: 600,
                                textTransform: "uppercase",
                                letterSpacing: "0.05em",
                                color: "var(--color-text-secondary)",
                                marginBottom: "var(--spacing-xs)",
                              }}
                            >
                              New Password
                            </div>
                            <div
                              style={{
                                display: "flex",
                                gap: "var(--spacing-xs)",
                                alignItems: "center",
                              }}
                            >
                              <input
                                type="password"
                                placeholder="Minimum 8 characters"
                                value={editPassword}
                                onChange={(e) => setEditPassword(e.target.value)}
                                style={{ flex: 1 }}
                              />
                              <button
                                className="btn btn-sm"
                                onClick={() => {
                                  setEditPassword("");
                                  setShowPasswordReset(false);
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}

                        <div
                          style={{
                            display: "flex",
                            gap: "var(--spacing-xs)",
                            marginTop: "var(--spacing-sm)",
                          }}
                        >
                          <button
                            className="btn btn-sm"
                            onClick={() => saveEdit(u.id)}
                            disabled={saving || editRoles.length === 0}
                          >
                            {saving ? "Saving..." : "Save"}
                          </button>
                          <button className="btn btn-sm" onClick={cancelEdit}>
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <RoleBadges roles={u.roles && u.roles.length > 0 ? u.roles : [u.role]} />
                    )}
                  </td>
                  <td
                    style={{
                      fontSize: "0.85rem",
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    {u.capabilities.length} {u.capabilities.length === 1 ? "capability" : "capabilities"}
                  </td>
                  <td
                    style={{
                      color: "var(--color-text-secondary)",
                      fontSize: "0.85rem",
                    }}
                  >
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    {editingUserId !== u.id && (
                      <button
                        className="btn btn-sm"
                        onClick={() => startEdit(u)}
                      >
                        Edit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
