// frontend/src/App.js
//
// Day 6 — 新增 Polling：提交后每 3 秒查一次状态，直到 completed/failed
//
// 改动点：
// 1. 新增 useRef（用于存 interval ID）
// 2. 新增 useEffect cleanup（组件卸载时停止 polling）
// 3. 新增 pollingOrderId state（记录正在 polling 的订单 ID）
// 4. 改写 handleSubmit（提交后启动 polling，不再直接显示结果）
// 5. 新增 pollOrderStatus 函数（polling 核心逻辑）
// 6. 新增"正在生成中"的 UI 状态

// ===================== 改动 1：新增 useRef 和 useEffect =====================
import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://sq03jeg8gg.execute-api.eu-north-1.amazonaws.com';

// Polling 配置常量
const POLL_INTERVAL = 3000;  // 每 3 秒查一次
const MAX_POLL_COUNT = 40;   // 最多查 40 次（3秒×40 = 2分钟后放弃）

function App() {
  // ============ 表单相关 state ============
  const [formData, setFormData] = useState({
    patient_first_name: '',
    patient_last_name: '',
    patient_mrn: '',
    patient_dob: '',
    provider_name: '',
    provider_npi: '',
    medication_name: '',
    primary_diagnosis: '',
    additional_diagnoses: '',
    medication_history: '',
    patient_records: '',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // ============ 搜索相关 state ============
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);

  // ===================== 改动 2：Polling 相关 state =====================
  // pollingOrderId：当前正在 polling 的订单 ID（null = 没在 polling）
  const [pollingOrderId, setPollingOrderId] = useState(null);

  // useRef 存 interval ID：为什么用 useRef 而不是 useState？
  // 因为 clearInterval 需要拿到最新的 interval ID，
  // useState 在 setInterval 的回调里会拿到旧值（闭包陷阱）
  // useRef 的 .current 永远是最新值
  const pollingIntervalRef = useRef(null);
  const pollCountRef = useRef(0);  // 已经 poll 了多少次

  // ===================== 改动 3：组件卸载时清理 =====================
  // 防止用户关掉页面后 polling 还在跑（内存泄漏）
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // ============================================================
  // 搜索订单（和之前一样，没改动）
  // ============================================================
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    setSelectedOrder(null);
    try {
      const response = await axios.get(`${API_URL}/orders`, {
        params: { order_id: searchQuery }
      });
      setSearchResults(response.data);
    } catch (err) {
      console.error('Search failed:', err);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  // ============================================================
  // 下载 Care Plan（和之前一样，没改动）
  // ============================================================
  const handleDownload = (orderId) => {
    window.open(`${API_URL}/api/orders/${orderId}/careplan/download`, '_blank');
  };

  // ============================================================
  // 表单输入处理（和之前一样，没改动）
  // ============================================================
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  // ===================== 改动 4：Polling 核心函数 =====================
  // 
  // 这个函数会被 setInterval 每 3 秒调用一次
  // 它做的事：GET /api/orders/{id}/status/ → 看 status → 决定是否停止
  //
  const pollOrderStatus = async (orderId) => {
    pollCountRef.current += 1;  // 计数 +1

    try {
      const response = await axios.get(`${API_URL}/orders`, {
        params: { order_id: orderId }
      });
      const data = response.data;

      if (data.status === 'completed' || data.status === 'failed') {
        // ======== 终止条件：任务完成或失败 ========
        clearInterval(pollingIntervalRef.current);  // 停止 polling
        pollingIntervalRef.current = null;
        pollCountRef.current = 0;
        setPollingOrderId(null);  // 清除"正在 polling"状态
        setLoading(false);        // 按钮恢复可用
        setResult(data);          // 把结果交给 UI 显示
      }

      // 如果 status 是 pending 或 processing，什么都不做，等下一次 poll

    } catch (err) {
      console.error('Polling error:', err);
      // 网络错误不停止 polling，下次再试
      // 但如果已经超过最大次数，就放弃
    }

    // ======== 超时保护：防止无限 polling ========
    if (pollCountRef.current >= MAX_POLL_COUNT) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      pollCountRef.current = 0;
      setPollingOrderId(null);
      setLoading(false);
      setError('Care plan generation timed out. Please check back later or try again.');
    }
  };

  // ===================== 改动 5：重写 handleSubmit =====================
  //
  // 之前的流程：POST → 拿到结果 → 直接显示
  // 现在的流程：POST → 拿到 order_id → 启动 polling → polling 拿到结果 → 显示
  //
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    setPollingOrderId(null);

    // 如果有之前的 polling 在跑，先停掉
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    const payload = {
      patient: {
        first_name: formData.patient_first_name,
        last_name: formData.patient_last_name,
        mrn: formData.patient_mrn,
        dob: formData.patient_dob,
      },
      provider: {
        name: formData.provider_name,
        npi: formData.provider_npi,
      },
      medication_name: formData.medication_name,
      primary_diagnosis: formData.primary_diagnosis,
      additional_diagnoses: formData.additional_diagnoses
        ? formData.additional_diagnoses.split(',').map(s => s.trim()).filter(Boolean)
        : [],
      medication_history: formData.medication_history
        ? formData.medication_history.split(',').map(s => s.trim()).filter(Boolean)
        : [],
      patient_records: formData.patient_records || "",
    };

    try {
      // 第 1 步：POST 提交订单，拿到 202 + order_id
      const response = await axios.post(`${API_URL}/orders`, payload);
      const orderId = response.data.order_id;

      // 第 2 步：记录正在 polling 的订单（UI 会显示"正在生成中"）
      setPollingOrderId(orderId);

      // 第 3 步：启动 polling
      // setInterval 会每 POLL_INTERVAL 毫秒执行一次 pollOrderStatus
      // 注意：setLoading 保持 true，所以按钮还是禁用状态
      pollCountRef.current = 0;
      pollingIntervalRef.current = setInterval(
        () => pollOrderStatus(orderId),
        POLL_INTERVAL
      );

    } catch (err) {
      // POST 本身失败（网络错误、服务器 500 等）
      setLoading(false);
      setError(
        err.response?.data
          ? JSON.stringify(err.response.data, null, 2)
          : err.message
      );
    }
    // 注意：这里没有 finally { setLoading(false) }
    // 因为 loading 要一直保持到 polling 结束才关掉
  };

  // ============================================================
  // 渲染 UI
  // ============================================================
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#c00', borderBottom: '2px solid #c00', paddingBottom: '10px' }}>
        🏥 CVS CarePlan Generator
      </h1>

      {/* ================================================================
          搜索区域（和之前一样，没改动）
          ================================================================ */}
      <fieldset style={{ ...fieldsetStyle, backgroundColor: '#f8f9fa' }}>
        <legend style={legendStyle}>🔍 Search Past Orders</legend>
        <p style={{ color: '#666', fontSize: '13px', margin: '0 0 10px' }}>
          Search by patient name, MRN, or medication name
        </p>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="e.g. Jane, 123456, IVIG..."
            style={{ ...inputStyle, flex: 1 }}
          />
          <button
            type="button"
            onClick={handleSearch}
            disabled={searchLoading}
            style={{
              ...buttonStyle,
              width: 'auto',
              padding: '8px 24px',
              marginTop: 0,
              fontSize: '14px',
              backgroundColor: '#333',
            }}
          >
            {searchLoading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <p style={{ fontSize: '13px', color: '#666', margin: '0 0 8px' }}>
              Found {searchResults.length} order(s):
            </p>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: '#e9ecef', textAlign: 'left' }}>
                  <th style={thStyle}>ID</th>
                  <th style={thStyle}>Patient</th>
                  <th style={thStyle}>MRN</th>
                  <th style={thStyle}>Medication</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {searchResults.map((order) => (
                  <tr key={order.id} style={{ borderBottom: '1px solid #ddd' }}>
                    <td style={tdStyle}>#{order.id}</td>
                    <td style={tdStyle}>{order.patient_first_name} {order.patient_last_name}</td>
                    <td style={tdStyle}>{order.patient_mrn}</td>
                    <td style={tdStyle}>{order.medication_name}</td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '10px',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        color: 'white',
                        backgroundColor:
                          order.status === 'completed' ? '#28a745' :
                            order.status === 'failed' ? '#dc3545' :
                              order.status === 'processing' ? '#ffc107' : '#6c757d',
                      }}>
                        {order.status}
                      </span>
                    </td>
                    <td style={tdStyle}>{order.order_date}</td>
                    <td style={tdStyle}>
                      {order.status === 'completed' && (
                        <>
                          <button
                            onClick={() => setSelectedOrder(
                              selectedOrder?.id === order.id ? null : order
                            )}
                            style={actionBtnStyle}
                          >
                            {selectedOrder?.id === order.id ? '▲ Hide' : '👁 View'}
                          </button>
                          {' '}
                          <button
                            onClick={() => handleDownload(order.id)}
                            style={{ ...actionBtnStyle, backgroundColor: '#28a745' }}
                          >
                            📥 Download
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {searchResults.length === 0 && searchQuery && !searchLoading && (
          <p style={{ color: '#999', fontSize: '13px', marginTop: '10px' }}>
            No orders found for "{searchQuery}"
          </p>
        )}

        {selectedOrder && (
          <div style={{
            marginTop: '12px',
            padding: '15px',
            backgroundColor: '#fff',
            border: '1px solid #ddd',
            borderRadius: '6px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h3 style={{ margin: 0, fontSize: '15px' }}>
                Care Plan — Order #{selectedOrder.id} | {selectedOrder.patient_first_name} {selectedOrder.patient_last_name} | {selectedOrder.medication_name}
              </h3>
              <button
                onClick={() => handleDownload(selectedOrder.id)}
                style={{ ...actionBtnStyle, backgroundColor: '#28a745' }}
              >
                📥 Download .txt
              </button>
            </div>
            <div style={{
              whiteSpace: 'pre-wrap',
              fontFamily: 'Georgia, serif',
              fontSize: '13px',
              lineHeight: '1.6',
              maxHeight: '400px',
              overflowY: 'auto',
              padding: '10px',
              backgroundColor: '#fafafa',
              border: '1px solid #eee',
              borderRadius: '4px',
            }}>
              {selectedOrder.care_plan?.content || selectedOrder.care_plan}
            </div>
          </div>
        )}
      </fieldset>

      {/* ================================================================
          提交新订单的表单（和之前一样，没改动）
          ================================================================ */}
      <h2 style={{ fontSize: '18px', color: '#333', marginTop: '30px' }}>📝 New Order</h2>

      <form onSubmit={handleSubmit}>
        <fieldset style={fieldsetStyle}>
          <legend style={legendStyle}>Patient Information</legend>
          <div style={rowStyle}>
            <label style={labelStyle}>
              First Name *
              <input name="patient_first_name" value={formData.patient_first_name}
                onChange={handleChange} required style={inputStyle} />
            </label>
            <label style={labelStyle}>
              Last Name *
              <input name="patient_last_name" value={formData.patient_last_name}
                onChange={handleChange} required style={inputStyle} />
            </label>
          </div>
          <div style={rowStyle}>
            <label style={labelStyle}>
              MRN (6 digits) *
              <input name="patient_mrn" value={formData.patient_mrn}
                onChange={handleChange} required style={inputStyle}
                placeholder="e.g. 123456" />
            </label>
            <label style={labelStyle}>
              Date of Birth *
              <input name="patient_dob" type="date" value={formData.patient_dob}
                onChange={handleChange} required style={inputStyle} />
            </label>
          </div>
        </fieldset>

        <fieldset style={fieldsetStyle}>
          <legend style={legendStyle}>Provider Information</legend>
          <div style={rowStyle}>
            <label style={labelStyle}>
              Provider Name *
              <input name="provider_name" value={formData.provider_name}
                onChange={handleChange} required style={inputStyle} />
            </label>
            <label style={labelStyle}>
              NPI (10 digits) *
              <input name="provider_npi" value={formData.provider_npi}
                onChange={handleChange} required style={inputStyle}
                placeholder="e.g. 1234567890" />
            </label>
          </div>
        </fieldset>

        <fieldset style={fieldsetStyle}>
          <legend style={legendStyle}>Medication & Diagnosis</legend>
          <div style={rowStyle}>
            <label style={labelStyle}>
              Medication Name *
              <input name="medication_name" value={formData.medication_name}
                onChange={handleChange} required style={inputStyle}
                placeholder="e.g. IVIG" />
            </label>
            <label style={labelStyle}>
              Primary Diagnosis (ICD-10) *
              <input name="primary_diagnosis" value={formData.primary_diagnosis}
                onChange={handleChange} required style={inputStyle}
                placeholder="e.g. G70.01" />
            </label>
          </div>
          <label style={{ ...labelStyle, display: 'block' }}>
            Additional Diagnoses (comma-separated, optional)
            <input name="additional_diagnoses" value={formData.additional_diagnoses}
              onChange={handleChange} style={inputStyle}
              placeholder="e.g. I10, K21.0" />
          </label>
          <label style={{ ...labelStyle, display: 'block' }}>
            Medication History (comma-separated, optional)
            <input name="medication_history" value={formData.medication_history}
              onChange={handleChange} style={inputStyle}
              placeholder="e.g. Pyridostigmine 60mg, Prednisone 10mg" />
          </label>
          <label style={{ ...labelStyle, display: 'block' }}>
            Patient Records / Notes (optional)
            <textarea name="patient_records" value={formData.patient_records}
              onChange={handleChange} style={{ ...inputStyle, height: '80px' }}
              placeholder="Any additional patient notes..." />
          </label>
        </fieldset>

        <button
          type="submit"
          disabled={loading}
          style={{
            ...buttonStyle,
            opacity: loading ? 0.6 : 1,
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '⏳ Generating Care Plan...' : '🚀 Submit Order & Generate Care Plan'}
        </button>
      </form>

      {/* ---- 错误提示 ---- */}
      {error && (
        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fee', border: '1px solid #c00', borderRadius: '6px' }}>
          <h3 style={{ color: '#c00', margin: '0 0 10px' }}>❌ Error</h3>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '14px' }}>{error}</pre>
        </div>
      )}

      {/* ===================== 改动 6：新增"正在生成中"状态 ===================== */}
      {/* 
        pollingOrderId 不为 null = 正在 polling = 正在等后台生成
        显示一个进度提示，让用户知道系统在工作
      */}
      {pollingOrderId && (
        <div style={{
          marginTop: '20px',
          padding: '20px',
          backgroundColor: '#e3f2fd',
          border: '1px solid #90caf9',
          borderRadius: '6px',
          textAlign: 'center',
        }}>
          <h3 style={{ color: '#1565c0', margin: '0 0 10px' }}>
            ⏳ Generating Care Plan...
          </h3>
          <p style={{ color: '#666', margin: 0, fontSize: '14px' }}>
            Order #{pollingOrderId} is being processed. Checking status every {POLL_INTERVAL / 1000} seconds...
          </p>
          <p style={{ color: '#999', margin: '5px 0 0', fontSize: '12px' }}>
            This usually takes 10-30 seconds. Please wait.
          </p>
        </div>
      )}

      {/* ---- 新生成的 Care Plan 结果 ---- */}
      {/* 改动 7：result 现在来自 polling 的 /status/ endpoint，字段名可能不同 */}
      {result && result.status === 'completed' && (
        <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f0fff0', border: '1px solid #0a0', borderRadius: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ color: '#0a0', margin: 0 }}>✅ Care Plan Generated</h2>
            <button
              onClick={() => handleDownload(result.order_id)}
              style={{ ...actionBtnStyle, backgroundColor: '#28a745', padding: '8px 20px', fontSize: '14px' }}
            >
              📥 Download .txt
            </button>
          </div>
          <p style={{ color: '#666', margin: '5px 0 15px', fontSize: '14px' }}>
            Order #{result.order_id}
          </p>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '4px',
            border: '1px solid #ddd',
            whiteSpace: 'pre-wrap',
            fontFamily: 'Georgia, serif',
            fontSize: '14px',
            lineHeight: '1.6',
          }}>
            {result.care_plan?.content || result.care_plan}
          </div>
        </div>
      )}

      {result && result.status === 'failed' && (
        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff3e0', border: '1px solid #ff9800', borderRadius: '6px' }}>
          <h3 style={{ color: '#ff9800' }}>⚠️ Care Plan Generation Failed</h3>
          <p>The LLM was unable to generate a care plan. Please try again.</p>
          <p style={{ fontSize: '14px', color: '#666' }}>Order #{result.order_id} has been saved with status: failed</p>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 样式（和之前一样，没改动）
// ============================================================
const fieldsetStyle = {
  border: '1px solid #ddd',
  borderRadius: '8px',
  padding: '15px 20px',
  marginBottom: '15px',
};

const legendStyle = {
  fontWeight: 'bold',
  color: '#333',
  fontSize: '16px',
};

const rowStyle = {
  display: 'flex',
  gap: '15px',
  marginBottom: '10px',
};

const labelStyle = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  fontSize: '14px',
  color: '#555',
  marginBottom: '8px',
};

const inputStyle = {
  padding: '8px 12px',
  border: '1px solid #ccc',
  borderRadius: '4px',
  fontSize: '14px',
  marginTop: '4px',
  width: '100%',
  boxSizing: 'border-box',
};

const buttonStyle = {
  width: '100%',
  padding: '14px',
  backgroundColor: '#c00',
  color: 'white',
  border: 'none',
  borderRadius: '6px',
  fontSize: '16px',
  fontWeight: 'bold',
  marginTop: '10px',
};

const actionBtnStyle = {
  padding: '4px 10px',
  fontSize: '12px',
  border: 'none',
  borderRadius: '4px',
  color: 'white',
  backgroundColor: '#007bff',
  cursor: 'pointer',
};

const thStyle = {
  padding: '8px 10px',
  borderBottom: '2px solid #ccc',
  fontSize: '13px',
};

const tdStyle = {
  padding: '8px 10px',
  verticalAlign: 'middle',
};

export default App;