"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  ProjectMember,
  User,
  addProjectMember,
  getProjectMembers,
  getUsers,
  removeProjectMember,
} from "@/lib/api";

export default function ProjectMembersPage() {
  const { id } = useParams<{ id: string }>();
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [adding, setAdding] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const memberEmails = useMemo(
    () => new Set(members.map((m) => m.email)),
    [members],
  );

  const filteredUsers = useMemo(() => {
    if (!query.trim()) return [];
    const lower = query.toLowerCase();
    return allUsers.filter(
      (u) =>
        !memberEmails.has(u.email) &&
        (u.display_name.toLowerCase().includes(lower) ||
          u.email.toLowerCase().includes(lower)),
    );
  }, [allUsers, memberEmails, query]);

  const load = () => {
    setLoading(true);
    Promise.all([
      getProjectMembers(id),
      getUsers(),
    ])
      .then(([m, u]) => {
        setMembers(m);
        setAllUsers(u);
      })
      .catch(() => setError("Failed to load members"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [id]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (u: User) => {
    setSelectedUser(u);
    setQuery(u.display_name);
    setShowDropdown(false);
  };

  const handleAdd = async () => {
    const target = selectedUser?.email || query.trim();
    if (!target) return;
    setAdding(true);
    setError(null);
    try {
      await addProjectMember(id, target);
      setQuery("");
      setSelectedUser(null);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to add member");
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (userId: string) => {
    try {
      await removeProjectMember(id, userId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to remove member");
    }
  };

  return (
    <div>
      <h2
        style={{
          fontSize: "1.1rem",
          fontWeight: 600,
          marginBottom: "var(--spacing-md)",
        }}
      >
        Members
      </h2>

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

      <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
        <div
          style={{
            display: "flex",
            gap: "var(--spacing-sm)",
            alignItems: "flex-end",
            position: "relative",
          }}
        >
          <div style={{ flex: 1, position: "relative" }}>
            <label
              style={{
                display: "block",
                fontSize: "0.85rem",
                fontWeight: 500,
                marginBottom: "4px",
                color: "var(--color-text-secondary)",
              }}
            >
              Add member
            </label>
            <input
              ref={inputRef}
              type="text"
              placeholder="Search by name or email..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedUser(null);
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              style={{ width: "100%" }}
            />
            {showDropdown && filteredUsers.length > 0 && (
              <div
                ref={dropdownRef}
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  right: 0,
                  zIndex: 10,
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  maxHeight: "240px",
                  overflowY: "auto",
                  marginTop: "4px",
                }}
              >
                {filteredUsers.map((u) => (
                  <div
                    key={u.id}
                    onClick={() => handleSelect(u)}
                    style={{
                      padding: "var(--spacing-sm) var(--spacing-md)",
                      cursor: "pointer",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "0.85rem",
                      borderBottom:
                        filteredUsers.indexOf(u) < filteredUsers.length - 1
                          ? "1px solid var(--color-border)"
                          : "none",
                    }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.background =
                        "var(--color-surface)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.background = "";
                    }}
                  >
                    <span style={{ fontWeight: 500 }}>
                      {u.display_name}
                    </span>
                    <span
                      style={{
                        color: "var(--color-text-secondary)",
                        fontSize: "0.8rem",
                      }}
                    >
                      {u.email}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleAdd}
            disabled={adding || !query.trim()}
          >
            {adding ? "Adding..." : "Add Member"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : members.length === 0 ? (
        <div className="card empty-state">No members yet.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Added</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.user_id}>
                  <td style={{ fontWeight: 500 }}>{m.display_name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {m.email}
                  </td>
                  <td
                    style={{
                      color: "var(--color-text-secondary)",
                      fontSize: "0.85rem",
                    }}
                  >
                    {new Date(m.added_at).toLocaleDateString()}
                  </td>
                  <td>
                    <button
                      onClick={() => handleRemove(m.user_id)}
                      style={{
                        background: "none",
                        border: "1px solid var(--color-border)",
                        borderRadius: "4px",
                        padding: "2px 8px",
                        fontSize: "0.8rem",
                        cursor: "pointer",
                        color: "var(--color-error, #d32f2f)",
                      }}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
