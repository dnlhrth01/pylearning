import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

function formatValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => formatValue(item)).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function humanize(label) {
  return label
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function DataTable({ rows }) {
  if (!rows || rows.length === 0) return <p className="muted">No records were found.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{cols.map((col) => <th key={col}>{humanize(col)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {cols.map((col) => <td key={`${index}-${col}`}>{formatValue(row[col])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function isoToDisplayDate(isoDate) {
  if (!isoDate) return "";
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

function getAuthPageFromHash() {
  return window.location.hash === "#/register" ? "register" : "login";
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("opslog_token") || "");
  const [user, setUser] = useState(JSON.parse(localStorage.getItem("opslog_user") || "null"));
  const [authPage, setAuthPage] = useState(getAuthPageFromHash());
  const [meta, setMeta] = useState({ roles: [], incident_statuses: [] });
  const [tab, setTab] = useState("dashboard");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [search, setSearch] = useState({ keyword: "", page: 1, page_size: 10, total: 0, rows: [] });

  const [registerForm, setRegisterForm] = useState({ full_name: "", email: "", username: "", password: "" });
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [createForm, setCreateForm] = useState({
    incident_id: "",
    error_name: "",
    component: "",
    root_cause: "",
    remark: "",
    action_taken: "",
    start_date: "",
    start_time: "",
    end_date: "",
    end_time: "",
  });
  const [updateId, setUpdateId] = useState("");
  const [loadedIncident, setLoadedIncident] = useState(null);
  const [updateForm, setUpdateForm] = useState({ root_cause: "", remark: "", action_taken: "", start_time: "", end_time: "", status: "" });
  const [deleteIncidentId, setDeleteIncidentId] = useState("");
  const [deleteRequests, setDeleteRequests] = useState([]);
  const [users, setUsers] = useState([]);
  const [roleForm, setRoleForm] = useState({ username: "", role: "" });
  const [statusForm, setStatusForm] = useState({ username: "", is_active: true });

  const menu = useMemo(() => {
    if (!user) return [];
    const items = ["dashboard", "search"];
    if (user.role !== "Manager") items.push("create", "update");
    if (user.role === "CS Leader") items.push("delete-request");
    if (user.role === "Manager" || user.role === "CS Leader") items.push("delete-approve");
    if (user.role === "Manager") items.push("users");
    return items;
  }, [user]);

  function clearAlerts() {
    setError("");
    setMessage("");
  }

  function navigateAuth(nextPage) {
    window.location.hash = nextPage === "register" ? "#/register" : "#/login";
    setAuthPage(nextPage);
    clearAlerts();
  }

  async function refreshDashboard(authToken = token) {
    const data = await api("/dashboard", "GET", authToken);
    setDashboard(data);
  }

  async function runSearch(next = search, authToken = token) {
    const query = `?keyword=${encodeURIComponent(next.keyword)}&page=${next.page}&page_size=${next.page_size}`;
    const data = await api(`/incidents${query}`, "GET", authToken);
    setSearch({ ...next, total: data.total, rows: data.rows });
  }

  async function bootstrap(authToken) {
    const [profile, metadata] = await Promise.all([
      api("/auth/me", "GET", authToken),
      api("/meta", "GET", authToken),
    ]);
    setUser(profile);
    setMeta(metadata);
    if (!roleForm.role && metadata.roles?.length) {
      setRoleForm((prev) => ({ ...prev, role: metadata.roles[0] }));
    }
    localStorage.setItem("opslog_user", JSON.stringify(profile));
    localStorage.setItem("opslog_token", authToken);
  }

  async function handleLogout() {
    try {
      if (token) {
        await api("/auth/logout", "POST", token);
      }
    } catch (_err) {
      // Ignore logout API errors and complete local logout.
    }
    setToken("");
    setUser(null);
    setDashboard(null);
    localStorage.removeItem("opslog_token");
    localStorage.removeItem("opslog_user");
    navigateAuth("login");
  }

  useEffect(() => {
    const onHashChange = () => setAuthPage(getAuthPageFromHash());
    window.addEventListener("hashchange", onHashChange);
    if (!window.location.hash) window.location.hash = "#/login";
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (!token) return;
    bootstrap(token)
      .then(() => Promise.all([refreshDashboard(token), runSearch({ ...search }, token)]))
      .catch(() => handleLogout());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!token || !menu.includes(tab)) setTab(menu[0] || "dashboard");
  }, [menu, tab, token]);

  useEffect(() => {
    if (!token) return;
    if (tab === "delete-approve") fetchDeleteRequests();
    if (tab === "users") fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, token]);

  async function handleLogin(event) {
    event.preventDefault();
    clearAlerts();
    try {
      const data = await api("/auth/login", "POST", "", loginForm);
      setToken(data.token);
      setMessage("Sign-in successful.");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    clearAlerts();
    try {
      await api("/auth/register", "POST", "", registerForm);
      setMessage("Registration completed. Please wait for manager role assignment.");
      setRegisterForm({ full_name: "", email: "", username: "", password: "" });
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateIncident(event) {
    event.preventDefault();
    clearAlerts();
    try {
      const payload = {
        ...createForm,
        start_date: isoToDisplayDate(createForm.start_date),
        end_date: isoToDisplayDate(createForm.end_date),
      };
      const data = await api("/incidents", "POST", token, payload);
      setMessage(`Incident ${data.incident_id} was created successfully.`);
      setCreateForm({
        incident_id: "",
        error_name: "",
        component: "",
        root_cause: "",
        remark: "",
        action_taken: "",
        start_date: "",
        start_time: "",
        end_date: "",
        end_time: "",
      });
      await Promise.all([refreshDashboard(), runSearch({ ...search })]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadIncident() {
    clearAlerts();
    try {
      const row = await api(`/incidents/${encodeURIComponent(updateId)}`, "GET", token);
      setLoadedIncident(row);
      setUpdateForm({
        root_cause: row.root_cause,
        remark: row.remark,
        action_taken: row.action_taken,
        start_time: row.start_time,
        end_time: row.end_time,
        status: row.status,
      });
      setMessage(`Incident ${row.incident_id} has been loaded.`);
    } catch (err) {
      setLoadedIncident(null);
      setError(err.message);
    }
  }

  async function handleUpdateIncident(event) {
    event.preventDefault();
    clearAlerts();
    if (!loadedIncident) return;
    try {
      await api(`/incidents/${encodeURIComponent(loadedIncident.incident_id)}`, "PATCH", token, updateForm);
      setMessage(`Incident ${loadedIncident.incident_id} was updated successfully.`);
      await Promise.all([refreshDashboard(), runSearch({ ...search }), loadIncident()]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteRequest(event) {
    event.preventDefault();
    clearAlerts();
    try {
      await api("/delete-requests", "POST", token, { incident_id: deleteIncidentId });
      setMessage("Delete request submitted successfully.");
      setDeleteIncidentId("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function fetchDeleteRequests() {
    try {
      const rows = await api("/delete-requests", "GET", token);
      setDeleteRequests(rows);
    } catch (err) {
      setError(err.message);
    }
  }

  async function approveDelete(incidentId) {
    clearAlerts();
    try {
      await api("/delete-requests/approve", "POST", token, { incident_id: incidentId });
      setMessage(`Incident ${incidentId} was deleted permanently.`);
      await Promise.all([fetchDeleteRequests(), refreshDashboard(), runSearch({ ...search })]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function fetchUsers() {
    try {
      const rows = await api("/users", "GET", token);
      setUsers(rows);
    } catch (err) {
      setError(err.message);
    }
  }

  async function assignRole(event) {
    event.preventDefault();
    clearAlerts();
    if (!roleForm.role) {
      setError("Please select a role before submitting.");
      return;
    }
    try {
      await api("/users/role", "POST", token, roleForm);
      setMessage("User role updated successfully.");
      await fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  async function updateStatus(event) {
    event.preventDefault();
    clearAlerts();
    try {
      await api("/users/status", "POST", token, statusForm);
      setMessage("User account status updated successfully.");
      await fetchUsers();
    } catch (err) {
      setError(err.message);
    }
  }

  if (!user) {
    const isLogin = authPage === "login";
    return (
      <main className="auth-layout">
        <section className="panel auth-panel">
          <h1>OpsLog</h1>
          <p className="muted">Operational incident management portal.</p>
          <div className="auth-switch">
            <button className={isLogin ? "active" : ""} onClick={() => navigateAuth("login")} type="button">Sign In</button>
            <button className={!isLogin ? "active" : ""} onClick={() => navigateAuth("register")} type="button">Register</button>
          </div>

          {error && <p className="error">{error}</p>}
          {message && <p className="message">{message}</p>}

          {isLogin ? (
            <form onSubmit={handleLogin} className="form">
              <h2>Sign In</h2>
              <input placeholder="Username" value={loginForm.username} onChange={(event) => setLoginForm({ ...loginForm, username: event.target.value })} />
              <input type="password" placeholder="Password" value={loginForm.password} onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })} />
              <button type="submit">Sign In</button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="form">
              <h2>Register Account</h2>
              <input placeholder="Full Name" value={registerForm.full_name} onChange={(event) => setRegisterForm({ ...registerForm, full_name: event.target.value })} />
              <input placeholder="Email Address" value={registerForm.email} onChange={(event) => setRegisterForm({ ...registerForm, email: event.target.value })} />
              <input placeholder="Username" value={registerForm.username} onChange={(event) => setRegisterForm({ ...registerForm, username: event.target.value })} />
              <input type="password" placeholder="Password" value={registerForm.password} onChange={(event) => setRegisterForm({ ...registerForm, password: event.target.value })} />
              <button type="submit">Complete Registration</button>
            </form>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="app-layout">
      <aside className="sidebar">
        <h1>OpsLog</h1>
        <p>{user.full_name}</p>
        <p className="role">{user.role}</p>
        {menu.map((item) => (
          <button className={tab === item ? "active" : ""} key={item} onClick={() => setTab(item)}>
            {humanize(item)}
          </button>
        ))}
        <button onClick={handleLogout}>Sign Out</button>
      </aside>

      <section className="content">
        {error && <p className="error">{error}</p>}
        {message && <p className="message">{message}</p>}

        {tab === "dashboard" && dashboard && (
          <div>
            <h2>Dashboard</h2>
            <div className="cards">
              <article className="card"><h3>Total Incidents</h3><p>{dashboard.total_incidents}</p></article>
              <article className="card"><h3>Open Cases</h3><p>{dashboard.open_cases}</p></article>
              <article className="card"><h3>Monitoring Cases</h3><p>{dashboard.monitoring_cases}</p></article>
              <article className="card"><h3>Resolved and Closed</h3><p>{dashboard.resolved_closed_cases}</p></article>
              <article className="card"><h3>Average Duration (min)</h3><p>{dashboard.avg_duration_minutes}</p></article>
              <article className="card"><h3>Last 7 Days</h3><p>{dashboard.incidents_last_7_days}</p></article>
            </div>
            <h3>Top Components</h3>
            <DataTable rows={dashboard.top_components} />
            <h3>Status Distribution</h3>
            <DataTable rows={dashboard.status_breakdown} />
          </div>
        )}

        {tab === "search" && (
          <div>
            <h2>Search Incidents</h2>
            <form className="form-inline" onSubmit={(event) => {
              event.preventDefault();
              runSearch({ ...search, page: 1 });
            }}>
              <input placeholder="Keyword across all fields" value={search.keyword} onChange={(event) => setSearch({ ...search, keyword: event.target.value })} />
              <input type="number" min="1" max="100" value={search.page_size} onChange={(event) => setSearch({ ...search, page_size: Number(event.target.value || 10) })} />
              <button type="submit">Search</button>
            </form>
            <form className="form-inline" onSubmit={(event) => {
              event.preventDefault();
              runSearch({ ...search });
            }}>
              <input type="number" min="1" value={search.page} onChange={(event) => setSearch({ ...search, page: Number(event.target.value || 1) })} />
              <button type="submit">Go To Page</button>
            </form>
            <p className="muted">Total records: {search.total}</p>
            <DataTable rows={search.rows} />
          </div>
        )}

        {tab === "create" && (
          <form onSubmit={handleCreateIncident} className="form">
            <h2>Create Incident</h2>
            <input placeholder="Incident ID (optional)" value={createForm.incident_id} onChange={(event) => setCreateForm({ ...createForm, incident_id: event.target.value })} />
            <input placeholder="Error Name" value={createForm.error_name} onChange={(event) => setCreateForm({ ...createForm, error_name: event.target.value })} />
            <input placeholder="Component" value={createForm.component} onChange={(event) => setCreateForm({ ...createForm, component: event.target.value })} />
            <textarea placeholder="Root Cause" value={createForm.root_cause} onChange={(event) => setCreateForm({ ...createForm, root_cause: event.target.value })} />
            <textarea placeholder="Remark" value={createForm.remark} onChange={(event) => setCreateForm({ ...createForm, remark: event.target.value })} />
            <textarea placeholder="Action Taken" value={createForm.action_taken} onChange={(event) => setCreateForm({ ...createForm, action_taken: event.target.value })} />
            <label>Start Date<input type="date" value={createForm.start_date} onChange={(event) => setCreateForm({ ...createForm, start_date: event.target.value })} /></label>
            <input placeholder="Start Time (HH:MM AM/PM)" value={createForm.start_time} onChange={(event) => setCreateForm({ ...createForm, start_time: event.target.value })} />
            <label>End Date<input type="date" value={createForm.end_date} onChange={(event) => setCreateForm({ ...createForm, end_date: event.target.value })} /></label>
            <input placeholder="End Time (HH:MM AM/PM)" value={createForm.end_time} onChange={(event) => setCreateForm({ ...createForm, end_time: event.target.value })} />
            <button type="submit">Create Incident</button>
          </form>
        )}

        {tab === "update" && (
          <div>
            <h2>Update Incident</h2>
            <form className="form-inline" onSubmit={(event) => {
              event.preventDefault();
              loadIncident();
            }}>
              <input placeholder="Incident ID" value={updateId} onChange={(event) => setUpdateId(event.target.value)} />
              <button type="submit">Load Incident</button>
            </form>
            {loadedIncident && (
              <form onSubmit={handleUpdateIncident} className="form">
                <p className="muted">{loadedIncident.incident_id} | {loadedIncident.error_name} | {loadedIncident.component}</p>
                <textarea value={updateForm.root_cause} onChange={(event) => setUpdateForm({ ...updateForm, root_cause: event.target.value })} />
                <textarea value={updateForm.remark} onChange={(event) => setUpdateForm({ ...updateForm, remark: event.target.value })} />
                <textarea value={updateForm.action_taken} onChange={(event) => setUpdateForm({ ...updateForm, action_taken: event.target.value })} />
                <input value={updateForm.start_time} onChange={(event) => setUpdateForm({ ...updateForm, start_time: event.target.value })} />
                <input value={updateForm.end_time} onChange={(event) => setUpdateForm({ ...updateForm, end_time: event.target.value })} />
                <select value={updateForm.status} onChange={(event) => setUpdateForm({ ...updateForm, status: event.target.value })}>
                  {Array.from(new Set([...(meta.incident_statuses || []), loadedIncident.status])).map((status) => (
                    <option key={status} value={status}>{status}</option>
                  ))}
                </select>
                <button type="submit">Update Incident</button>
              </form>
            )}
          </div>
        )}

        {tab === "delete-request" && (
          <form className="form" onSubmit={handleDeleteRequest}>
            <h2>Request Incident Deletion</h2>
            <input placeholder="Incident ID" value={deleteIncidentId} onChange={(event) => setDeleteIncidentId(event.target.value)} />
            <button type="submit">Submit Request</button>
          </form>
        )}

        {tab === "delete-approve" && (
          <div>
            <h2>Deletion Approvals</h2>
            <button onClick={fetchDeleteRequests}>Refresh Requests</button>
            <DataTable rows={deleteRequests} />
            <div className="actions">
              {deleteRequests.filter((request) => request.status === "Pending").map((request) => (
                <button key={request.incident_id} onClick={() => approveDelete(request.incident_id)}>
                  Approve {request.incident_id}
                </button>
              ))}
            </div>
          </div>
        )}

        {tab === "users" && (
          <div>
            <h2>User Administration</h2>
            <button onClick={fetchUsers}>Refresh Users</button>
            <DataTable rows={users} />
            <form className="form-inline" onSubmit={assignRole}>
              <input placeholder="Username" value={roleForm.username} onChange={(event) => setRoleForm({ ...roleForm, username: event.target.value })} />
              <select value={roleForm.role} onChange={(event) => setRoleForm({ ...roleForm, role: event.target.value })}>
                <option value="">Select Role</option>
                {meta.roles.map((role) => <option key={role} value={role}>{role}</option>)}
              </select>
              <button type="submit">Assign Role</button>
            </form>
            <form className="form-inline" onSubmit={updateStatus}>
              <input placeholder="Username" value={statusForm.username} onChange={(event) => setStatusForm({ ...statusForm, username: event.target.value })} />
              <select value={statusForm.is_active ? "1" : "0"} onChange={(event) => setStatusForm({ ...statusForm, is_active: event.target.value === "1" })}>
                <option value="1">Activate Account</option>
                <option value="0">Suspend Account</option>
              </select>
              <button type="submit">Update Account Status</button>
            </form>
          </div>
        )}
      </section>
    </main>
  );
}

