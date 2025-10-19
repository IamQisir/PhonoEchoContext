import streamlit as st
import streamlit.components.v1 as components

# 初始化 session state
if "test" not in st.session_state:
    st.session_state["test"] = None

html_code = """
<style>
    table {
        width: 100%;
        border-collapse: collapse;
    }
    td, th {
        border: 1px solid #ddd;
        padding: 8px;
        cursor: pointer;
    }
    td:hover {
        background-color: #f0f0f0;
    }
    th {
        background-color: #4CAF50;
        color: white;
    }
    .selected {
        background-color: #90EE90;
    }
</style>

<table id="myTable">
    <tr>
        <th>Word</th>
        <th>Score1</th>
        <th>Score2</th>
    </tr>
    <tr onclick="handleClick(10, 15, this)">
        <td>apple</td>
        <td>10</td>
        <td>15</td>
    </tr>
    <tr onclick="handleClick(20, 25, this)">
        <td>banana</td>
        <td>20</td>
        <td>25</td>
    </tr>
    <tr onclick="handleClick(30, 35, this)">
        <td>cherry</td>
        <td>30</td>
        <td>35</td>
    </tr>
</table>

<script>
    function handleClick(score1, score2, row) {
        // 移除之前的高亮
        document.querySelectorAll('tr').forEach(r => {
            r.classList.remove('selected');
        });
        // 添加当前行高亮
        row.classList.add('selected');
        
        // 通过 Streamlit 的 API 传递数据回 Python
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: [score1, score2]
        }, '*');
    }
</script>
"""

# 使用 components.html 接收返回值
result = components.html(html_code, height=200)

# 检查 result 是否为有效的列表数据
if result and isinstance(result, list) and len(result) == 2:
    st.session_state["test"] = result
    print(result)
    st.rerun()  # 重新运行以更新显示

# 显示选中的值（只有当真正选择后才显示）
if st.session_state["test"] is not None:
    st.success(f"已选择: {st.session_state['test']}")
    st.write(
        f"Score1: {st.session_state['test'][0]}, Score2: {st.session_state['test'][1]}"
    )
else:
    st.info("👆 请点击表格中的任意行")
