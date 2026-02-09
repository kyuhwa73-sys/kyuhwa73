import { useCallback, useRef } from 'react';
import { useReactFlow } from '@xyflow/react';
import { toPng } from 'html-to-image';
import { useMindMapStore } from '../store/useMindMapStore';
import { exportTreeAsJson, importTreeFromJson, downloadFile } from '../utils/storage';

export default function Toolbar() {
  const { tree, undo, redo, resetToNew, importTree, past, future } = useMindMapStore();
  const { fitView } = useReactFlow();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleNew = useCallback(() => {
    if (window.confirm('현재 마인드맵을 초기화하시겠습니까?\n(저장되지 않은 변경사항이 사라집니다.)')) {
      resetToNew();
    }
  }, [resetToNew]);

  const handleExportPng = useCallback(() => {
    const el = document.querySelector('.react-flow') as HTMLElement;
    if (!el) return;

    toPng(el, {
      backgroundColor: '#1a1a2e',
      quality: 1,
      pixelRatio: 2,
    }).then((dataUrl) => {
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `mindmap-${Date.now()}.png`;
      a.click();
    }).catch((err) => {
      console.error('PNG 내보내기 실패:', err);
      alert('PNG 내보내기에 실패했습니다.');
    });
  }, []);

  const handleExportJson = useCallback(() => {
    const json = exportTreeAsJson(tree);
    downloadFile(json, `mindmap-${Date.now()}.json`, 'application/json');
  }, [tree]);

  const handleImportJson = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const json = ev.target?.result as string;
          const imported = importTreeFromJson(json);
          importTree(imported);
        } catch (err) {
          alert('JSON 파일을 불러올 수 없습니다.\n올바른 마인드맵 JSON 형식인지 확인해주세요.');
          console.error(err);
        }
      };
      reader.readAsText(file);
      // reset input so the same file can be re-imported
      e.target.value = '';
    },
    [importTree],
  );

  const handleFitView = useCallback(() => {
    fitView({ padding: 0.2, duration: 300 });
  }, [fitView]);

  const handleSave = useCallback(() => {
    // 이미 autosave 되어있지만, 명시적 확인 메시지 제공
    const json = exportTreeAsJson(tree);
    localStorage.setItem('mindmap-editor-data', JSON.stringify(JSON.parse(json)));
    alert('마인드맵이 저장되었습니다.');
  }, [tree]);

  const handlePrint = useCallback(() => {
    const el = document.querySelector('.react-flow') as HTMLElement;
    if (!el) return;

    toPng(el, {
      backgroundColor: '#ffffff',
      quality: 1,
      pixelRatio: 2,
    }).then((dataUrl) => {
      const printWindow = window.open('', '_blank');
      if (!printWindow) {
        alert('팝업이 차단되었습니다. 팝업 허용 후 다시 시도해주세요.');
        return;
      }
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>마인드맵 인쇄</title>
            <style>
              body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
              img { max-width: 100%; height: auto; }
              @media print {
                body { margin: 0; }
                img { max-width: 100%; page-break-inside: avoid; }
              }
            </style>
          </head>
          <body>
            <img src="${dataUrl}" />
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.onload = () => {
        printWindow.print();
      };
    }).catch((err) => {
      console.error('인쇄 실패:', err);
      alert('인쇄에 실패했습니다.');
    });
  }, []);

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button className="toolbar-btn" onClick={handleNew} title="새 마인드맵">
          <span className="btn-icon">📄</span> 새로 만들기
        </button>
        <button className="toolbar-btn" onClick={handleSave} title="저장 (Ctrl+S)">
          <span className="btn-icon">💾</span> 저장
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button className="toolbar-btn" onClick={handleExportPng} title="PNG로 내보내기">
          <span className="btn-icon">🖼️</span> PNG 내보내기
        </button>
        <button className="toolbar-btn" onClick={handleImportJson} title="JSON 불러오기">
          <span className="btn-icon">📂</span> JSON 불러오기
        </button>
        <button className="toolbar-btn" onClick={handleExportJson} title="JSON으로 내보내기">
          <span className="btn-icon">📤</span> JSON 내보내기
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button
          className="toolbar-btn"
          onClick={undo}
          disabled={past.length === 0}
          title="실행 취소 (Ctrl+Z)"
        >
          <span className="btn-icon">↩️</span> 실행 취소
        </button>
        <button
          className="toolbar-btn"
          onClick={redo}
          disabled={future.length === 0}
          title="다시 실행 (Ctrl+Y)"
        >
          <span className="btn-icon">↪️</span> 다시 실행
        </button>
      </div>

      <div className="toolbar-divider" />

      <div className="toolbar-group">
        <button className="toolbar-btn" onClick={handleFitView} title="화면에 맞추기">
          <span className="btn-icon">🔍</span> 화면 맞춤
        </button>
        <button className="toolbar-btn" onClick={handlePrint} title="인쇄 (Ctrl+P)">
          <span className="btn-icon">🖨️</span> 인쇄
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
    </div>
  );
}
