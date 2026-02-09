import { memo, useState, useRef, useEffect, useCallback } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { useMindMapStore } from '../store/useMindMapStore';

interface MindMapNodeData {
  text: string;
  isRoot: boolean;
  isSelected: boolean;
  isEditing: boolean;
  collapsed: boolean;
  hasChildren: boolean;
  depth: number;
  style: {
    backgroundColor: string;
    borderColor: string;
    fontSize: number;
  };
  [key: string]: unknown;
}

function MindMapNodeComponent({ id, data }: NodeProps) {
  const d = data as unknown as MindMapNodeData;
  const {
    setSelectedNodeId,
    setEditingNodeId,
    updateNodeText,
    toggleCollapse,
    pushSnapshot,
  } = useMindMapStore();

  const [editText, setEditText] = useState(d.text);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (d.isEditing && inputRef.current) {
      setEditText(d.text);
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [d.isEditing, d.text]);

  const handleDoubleClick = useCallback(() => {
    setSelectedNodeId(id);
    setEditingNodeId(id);
  }, [id, setSelectedNodeId, setEditingNodeId]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedNodeId(id);
  }, [id, setSelectedNodeId]);

  const commitEdit = useCallback(() => {
    const trimmed = editText.trim();
    if (trimmed && trimmed !== d.text) {
      pushSnapshot();
      updateNodeText(id, trimmed);
    }
    setEditingNodeId(null);
  }, [editText, d.text, id, pushSnapshot, updateNodeText, setEditingNodeId]);

  const cancelEdit = useCallback(() => {
    setEditText(d.text);
    setEditingNodeId(null);
  }, [d.text, setEditingNodeId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation();
      if (e.key === 'Enter') {
        e.preventDefault();
        commitEdit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancelEdit();
      }
    },
    [commitEdit, cancelEdit],
  );

  const handleCollapseClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      toggleCollapse(id);
    },
    [id, toggleCollapse],
  );

  const isLight = isLightColor(d.style.backgroundColor);

  return (
    <div
      className={`mindmap-node ${d.isSelected ? 'selected' : ''} ${d.isRoot ? 'root' : ''}`}
      style={{
        backgroundColor: d.style.backgroundColor,
        borderColor: d.isSelected ? '#FFD700' : d.style.borderColor,
        borderWidth: d.isSelected ? 3 : 2,
        fontSize: d.style.fontSize,
        color: isLight ? '#1a1a1a' : '#ffffff',
      }}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
    >
      {!d.isRoot && (
        <Handle type="target" position={Position.Top} className="mindmap-handle" />
      )}

      {d.isEditing ? (
        <input
          ref={inputRef}
          className="mindmap-node-input"
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commitEdit}
          style={{ fontSize: d.style.fontSize, color: isLight ? '#1a1a1a' : '#ffffff' }}
        />
      ) : (
        <span className="mindmap-node-text">{d.text}</span>
      )}

      <Handle type="source" position={Position.Bottom} className="mindmap-handle" />

      {d.hasChildren && (
        <button
          className="collapse-btn"
          onClick={handleCollapseClick}
          title={d.collapsed ? '펼치기' : '접기'}
        >
          {d.collapsed ? '+' : '−'}
        </button>
      )}
    </div>
  );
}

function isLightColor(hex: string): boolean {
  const c = hex.replace('#', '');
  const r = parseInt(c.substring(0, 2), 16);
  const g = parseInt(c.substring(2, 4), 16);
  const b = parseInt(c.substring(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 150;
}

export default memo(MindMapNodeComponent);
