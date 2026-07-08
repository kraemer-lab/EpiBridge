"use client";

import { useEffect, useState, useCallback } from "react";
import { AuditEvent, getAuditEvents } from "@/lib/api";

const EVENT_TYPES = [
  { value: "", label: "All events" },
  { value: "project.created", label: "Project created" },
  { value: "bundle.created", label: "Bundle created" },
  { value: "bundle.submitted", label: "Bundle submitted" },
  { value: "bundle.approved", label: "Bundle approved" },
  { value: "bundle.rejected", label: "Bundle rejected" },
  { value: "execution.requested", label: "Execution requested" },
  { value: "execution.completed", label: "Execution completed" },
  { value: "execution.failed", label: "Execution failed" },
  { value: "output_set.created", label: "Output set created" },
  { value: "output_set.approved", label: "Output approved" },
  { value: "output_set.released", label: "Output released" },
  { value: "user.created", label: "User created" },
];

const PAGE_SIZE = 30;

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function AdminAuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState("");

  const load = useCallback(async (currentOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = { limit: PAGE_SIZE, offset: currentOffset };
      if (eventTypeFilter) {
        params.event_type = eventTypeFilter;
      }
      const result = await getAuditEvents(params);
      setEvents(result.items);
      setTotal(result.total);
    } catch {
      setError("Failed to load audit events");
    } finally {
      setLoading(false);
    }
  }, [eventTypeFilter]);

  useEffect(() => {
    setOffset(0);
    load(0);
  }, [load]);

  const handlePage = (newOffset: number) => {
    setOffset(newOffset);
    load(newOffset);
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Audit Log
      </h2>

      <div style={{ marginBottom: "var(--spacing-md)" }}>
        <label style={{ fontSize: "0.85rem", marginRight: "var(--spacing-sm)" }}>
          Event type:
        </label>
        <select
          value={eventTypeFilter}
          onChange={(e) => setEventTypeFilter(e.target.value)}
          style={{
            padding: "4px 8px",
            borderRadius: "4px",
            border: "1px solid var(--color-border, #ddd)",
            fontSize: "0.85rem",
          }}
        >
          {EVENT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : events.length === 0 ? (
        <div className="card empty-state">No audit events found.</div>
      ) : (
        <>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Resource</th>
                  <th>Actor</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          background: "#f0f4ff",
                          color: "#1565c0",
                        }}
                      >
                        {e.event_type}
                      </span>
                    </td>
                    <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                      {e.resource_type}
                    </td>
                    <td style={{ fontSize: "0.85rem" }}>
                      {e.actor_display_name}
                    </td>
                    <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                      {formatTime(e.occurred_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                gap: "var(--spacing-sm)",
                marginTop: "var(--spacing-md)",
                alignItems: "center",
              }}
            >
              <button
                className="btn btn-sm"
                disabled={offset === 0}
                onClick={() => handlePage(offset - PAGE_SIZE)}
                style={{ opacity: offset === 0 ? 0.5 : 1 }}
              >
                Previous
              </button>
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn btn-sm"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => handlePage(offset + PAGE_SIZE)}
                style={{ opacity: offset + PAGE_SIZE >= total ? 0.5 : 1 }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
