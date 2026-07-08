"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ProjectMember, addProjectMember, getProjectMembers, removeProjectMember } from "@/lib/api";

export default function ProjectMembersPage() {
  const { id } = useParams<{ id: string }>();
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [adding, setAdding] = useState(false);

  const load = () => {
    setLoading(true);
    getProjectMembers(id)
      .then(setMembers)
      .catch(() => setError("Failed to load members"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [id]);

  const handleAdd = async () => {
    if (!email.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await addProjectMember(id, email.trim());
      setEmail("");
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
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Members
      </h2>

      {error && (
        <div className="card" style={{ background: "var(--color-error-bg, #fdecea)", color: "var(--color-error, #d32f2f)", marginBottom: "var(--spacing-md)", padding: "var(--spacing-sm)" }}>
          {error}
        </div>
      )}

      <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
        <div style={{ display: "flex", gap: "var(--spacing-sm)", alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "4px", color: "var(--color-text-secondary)" }}>
              Add member by email
            </label>
            <input
              type="email"
              placeholder="user@institution.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              style={{ width: "100%" }}
            />
          </div>
          <button onClick={handleAdd} disabled={adding || !email.trim()}>
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
                <th></th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.user_id}>
                  <td style={{ fontWeight: 500 }}>{m.display_name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>{m.email}</td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
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
