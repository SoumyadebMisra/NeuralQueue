import { useState } from "react";

const PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];

function generateId() {
return Math.random().toString(36).substring(2, 8);
}

export default function NeuralQueueDashboard() {
const [tasks, setTasks] = useState([]);
const [workers] = useState([
{ id: "worker-1", status: "idle" },
{ id: "worker-2", status: "idle" },
{ id: "worker-3", status: "idle" },
]);

const [form, setForm] = useState({
type: "summarization",
priority: "MEDIUM",
});

const submitTask = () => {
const newTask = {
id: generateId(),
type: form.type,
priority: form.priority,
status: "queued",
};
setTasks((prev) => [newTask, ...prev]);
};

return (
<div style={{ padding: 20, fontFamily: "sans-serif" }}> <h2>NeuralQueue Dashboard</h2>

  {/* Submit Task */}
  <div style={{ marginBottom: 20 }}>
    <h4>Submit Task</h4>
    <select
      value={form.type}
      onChange={(e) => setForm({ ...form, type: e.target.value })}
    >
      <option value="summarization">Summarization</option>
      <option value="embedding">Embedding</option>
    </select>

    <select
      value={form.priority}
      onChange={(e) => setForm({ ...form, priority: e.target.value })}
    >
      {PRIORITIES.map((p) => (
        <option key={p}>{p}</option>
      ))}
    </select>

    <button onClick={submitTask}>Add Task</button>
  </div>

  {/* Tasks */}
  <div style={{ marginBottom: 20 }}>
    <h4>Tasks</h4>
    <table border="1" cellPadding="8">
      <thead>
        <tr>
          <th>ID</th>
          <th>Type</th>
          <th>Priority</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((t) => (
          <tr key={t.id}>
            <td>{t.id}</td>
            <td>{t.type}</td>
            <td>{t.priority}</td>
            <td>{t.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>

  {/* Workers */}
  <div>
    <h4>Workers</h4>
    <ul>
      {workers.map((w) => (
        <li key={w.id}>
          {w.id} — {w.status}
        </li>
      ))}
    </ul>
  </div>
</div>

);
}
