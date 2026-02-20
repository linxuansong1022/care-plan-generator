// frontend/src/App.js
//
// Day 2 MVP 前端 — 新增：搜索历史订单 + 下载 Care Plan
//
// 页面结构：
// 1. 顶部搜索栏：输入关键词 → 搜索历史订单 → 点击查看/下载
// 2. 表单：填写信息 → 提交 → 显示新生成的 Care Plan
// 3. 结果区：显示 Care Plan 内容 + 下载按钮

import React, { useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
  const [searchQuery, setSearchQuery] = useState('');        // 搜索框里的文字
  const [searchResults, setSearchResults] = useState([]);     // 搜索结果列表
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);   // 用户点击查看的订单

  // ============================================================
  // 搜索订单
  // 发 GET /api/orders/?search=xxx 到后端
  // ============================================================
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearchLoading(true);
    setSelectedOrder(null);  // 清掉之前选中的
    try {
      const response = await axios.get(`${API_URL}/api/orders/`, {
        params: { search: searchQuery }
        // axios 会自动把 params 变成 URL 参数: ?search=xxx
      });
      setSearchResults(response.data);
    } catch (err) {
      console.error('Search failed:', err);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // 按回车也能搜索
  const handleSearchKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  // ============================================================
  // 下载 Care Plan
  // 原理：创建一个隐藏的 <a> 标签，设置 href 为下载 URL，模拟点击
  // ============================================================
  const handleDownload = (orderId) => {
    // 直接打开下载链接，浏览器会自动处理（因为后端设了 Content-Disposition）
    window.open(`${API_URL}/api/orders/${orderId}/careplan/download`, '_blank');
  };

  // ============================================================
  // 提交表单（和之前一样）
  // ============================================================
  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);

    const payload = {
      ...formData,
      additional_diagnoses: formData.additional_diagnoses
        ? formData.additional_diagnoses.split(',').map(s => s.trim()).filter(Boolean)
        : [],
      medication_history: formData.medication_history
        ? formData.medication_history.split(',').map(s => s.trim()).filter(Boolean)
        : [],
    };

    try {
      const response = await axios.post(`${API_URL}/api/orders/`, payload);
      setResult(response.data);
    } catch (err) {
      setError(
        err.response?.data
          ? JSON.stringify(err.response.data, null, 2)
          : err.message
      );
    } finally {
      setLoading(false);
    }
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
          搜索区域
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

        {/* ---- 搜索结果列表 ---- */}
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
                      {/* 查看按钮：点击后展开 care plan 内容 */}
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

        {/* ---- 搜索后没结果 ---- */}
        {searchResults.length === 0 && searchQuery && !searchLoading && (
          <p style={{ color: '#999', fontSize: '13px', marginTop: '10px' }}>
            No orders found for "{searchQuery}"
          </p>
        )}

        {/* ---- 展开查看某个历史 care plan ---- */}
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
              {selectedOrder.care_plan_content}
            </div>
          </div>
        )}
      </fieldset>

      {/* ================================================================
          提交新订单的表单（和之前一样）
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
          {loading ? '⏳ Generating Care Plan... (this may take 10-30 seconds)' : '🚀 Submit Order & Generate Care Plan'}
        </button>
      </form>

      {/* ---- 错误提示 ---- */}
      {error && (
        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fee', border: '1px solid #c00', borderRadius: '6px' }}>
          <h3 style={{ color: '#c00', margin: '0 0 10px' }}>❌ Error</h3>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '14px' }}>{error}</pre>
        </div>
      )}

      {/* ---- 新生成的 Care Plan 结果 ---- */}
      {result && result.status === 'completed' && (
        <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f0fff0', border: '1px solid #0a0', borderRadius: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2 style={{ color: '#0a0', margin: 0 }}>✅ Care Plan Generated</h2>
            <button
              onClick={() => handleDownload(result.id)}
              style={{ ...actionBtnStyle, backgroundColor: '#28a745', padding: '8px 20px', fontSize: '14px' }}
            >
              📥 Download .txt
            </button>
          </div>
          <p style={{ color: '#666', margin: '5px 0 15px', fontSize: '14px' }}>
            Order #{result.id} | {result.patient_first_name} {result.patient_last_name} | {result.medication_name}
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
            {result.care_plan_content}
          </div>
        </div>
      )}

      {result && result.status === 'failed' && (
        <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#fff3e0', border: '1px solid #ff9800', borderRadius: '6px' }}>
          <h3 style={{ color: '#ff9800' }}>⚠️ Care Plan Generation Failed</h3>
          <p>The LLM was unable to generate a care plan. Please try again.</p>
          <p style={{ fontSize: '14px', color: '#666' }}>Order #{result.id} has been saved with status: failed</p>
        </div>
      )}
    </div>
  );
}

// ============================================================
// 样式
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

// 表格里的小按钮
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
