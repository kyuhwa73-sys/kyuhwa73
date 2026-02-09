import { useMemo } from 'react';
import { useMindMapStore } from '../store/useMindMapStore';
import { findNode } from '../utils/tree';
import { getColorForDepth, getDepth } from '../utils/tree';

export default function PropertiesPanel() {
  const {
    tree,
    selectedNodeId,
    updateNodeStyle,
    addChild,
    deleteNode,
    setEditingNodeId,
  } = useMindMapStore();

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return findNode(tree, selectedNodeId);
  }, [tree, selectedNodeId]);

  const depth = useMemo(() => {
    if (!selectedNodeId) return 0;
    return getDepth(tree, selectedNodeId);
  }, [tree, selectedNodeId]);

  const isRoot = selectedNode?.id === tree.id;

  if (!selectedNode) {
    return (
      <div className="properties-panel">
        <div className="panel-header">노드 속성</div>
        <div className="panel-empty">
          노드를 선택하면<br />속성을 편집할 수 있습니다.
        </div>
        <div className="panel-shortcuts">
          <div className="panel-header">단축키</div>
          <div className="shortcut-item"><kbd>Tab</kbd> 자식 노드 추가</div>
          <div className="shortcut-item"><kbd>Enter</kbd> 형제 노드 추가</div>
          <div className="shortcut-item"><kbd>Delete</kbd> 노드 삭제</div>
          <div className="shortcut-item"><kbd>F2</kbd> / 더블클릭 편집</div>
          <div className="shortcut-item"><kbd>Esc</kbd> 편집 취소</div>
          <div className="shortcut-item"><kbd>Space</kbd> 접기/펼치기</div>
          <div className="shortcut-item"><kbd>Ctrl+Z</kbd> 실행 취소</div>
          <div className="shortcut-item"><kbd>Ctrl+Y</kbd> 다시 실행</div>
          <div className="shortcut-item"><kbd>Ctrl+S</kbd> 저장</div>
          <div className="shortcut-item"><kbd>Ctrl+P</kbd> 인쇄</div>
        </div>
      </div>
    );
  }

  const bgColor = selectedNode.style?.backgroundColor || getColorForDepth(depth);
  const borderColor = selectedNode.style?.borderColor || getColorForDepth(depth);
  const fontSize = selectedNode.style?.fontSize || (depth === 0 ? 18 : 14);

  return (
    <div className="properties-panel">
      <div className="panel-header">노드 속성</div>

      <div className="panel-section">
        <label className="panel-label">텍스트</label>
        <div className="panel-text-display">
          {selectedNode.text}
          <button
            className="panel-btn-small"
            onClick={() => setEditingNodeId(selectedNode.id)}
            title="편집"
          >
            ✏️
          </button>
        </div>
      </div>

      <div className="panel-section">
        <label className="panel-label">배경색</label>
        <div className="color-input-row">
          <input
            type="color"
            value={bgColor}
            onChange={(e) => updateNodeStyle(selectedNode.id, { backgroundColor: e.target.value })}
          />
          <span className="color-value">{bgColor}</span>
        </div>
      </div>

      <div className="panel-section">
        <label className="panel-label">테두리색</label>
        <div className="color-input-row">
          <input
            type="color"
            value={borderColor}
            onChange={(e) => updateNodeStyle(selectedNode.id, { borderColor: e.target.value })}
          />
          <span className="color-value">{borderColor}</span>
        </div>
      </div>

      <div className="panel-section">
        <label className="panel-label">글자 크기: {fontSize}px</label>
        <input
          type="range"
          min={10}
          max={32}
          value={fontSize}
          onChange={(e) =>
            updateNodeStyle(selectedNode.id, { fontSize: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div className="panel-section panel-actions">
        <button
          className="panel-btn add-btn"
          onClick={() => addChild(selectedNode.id)}
        >
          + 자식 노드 추가
        </button>
        {!isRoot && (
          <button
            className="panel-btn delete-btn"
            onClick={() => {
              if (window.confirm(`"${selectedNode.text}" 노드를 삭제하시겠습니까?\n(하위 노드도 함께 삭제됩니다.)`)) {
                deleteNode(selectedNode.id);
              }
            }}
          >
            🗑️ 노드 삭제
          </button>
        )}
      </div>

      <div className="panel-shortcuts">
        <div className="panel-header">단축키</div>
        <div className="shortcut-item"><kbd>Tab</kbd> 자식 노드 추가</div>
        <div className="shortcut-item"><kbd>Enter</kbd> 형제 노드 추가</div>
        <div className="shortcut-item"><kbd>Delete</kbd> 노드 삭제</div>
        <div className="shortcut-item"><kbd>F2</kbd> / 더블클릭 편집</div>
        <div className="shortcut-item"><kbd>Esc</kbd> 편집 취소</div>
        <div className="shortcut-item"><kbd>Space</kbd> 접기/펼치기</div>
        <div className="shortcut-item"><kbd>Ctrl+Z</kbd> 실행 취소</div>
        <div className="shortcut-item"><kbd>Ctrl+Y</kbd> 다시 실행</div>
        <div className="shortcut-item"><kbd>Ctrl+S</kbd> 저장</div>
        <div className="shortcut-item"><kbd>Ctrl+P</kbd> 인쇄</div>
      </div>
    </div>
  );
}
