// Lightweight Monaco loader and integration for the editor textarea (Sprint 1 start)
// This script replaces the <textarea id="snippetContent"> with a Monaco editor
// when the Code Studio tab is active. It uses the Monaco CDN to avoid build steps.
// Features implemented:
// - Syntax highlighting for the selected language
// - Ctrl+S to save (dispatches click on #btnSaveSnippet)
// - Ctrl+Enter to run (dispatches click on #btnRunSnippet)
// - Basic status updates (Ln/Col)

(function(){
  // Only run when Code Studio exists on the page
  var textarea = document.getElementById('snippetContent');
  if(!textarea) return;

  // Create a placeholder div for Monaco
  var editorDiv = document.createElement('div');
  editorDiv.id = 'monacoEditor';
  editorDiv.style.width = '100%';
  editorDiv.style.height = '100%';
  editorDiv.style.minHeight = '300px';
  editorDiv.style.display = 'none';

  textarea.parentNode.insertBefore(editorDiv, textarea);
  // hide the textarea but keep it in DOM for fallback
  textarea.style.display = 'none';

  // Load Monaco from CDN (unpkg). Use AMD loader pattern that Monaco supports.
  var loaderScript = document.createElement('script');
  loaderScript.src = 'https://unpkg.com/monaco-editor@0.42.0/min/vs/loader.js';
  loaderScript.onload = function(){
    // configure baseUrl so Monaco can load its workers
    require.config({ paths: { 'vs': 'https://unpkg.com/monaco-editor@0.42.0/min/vs' } });
    require(['vs/editor/editor.main'], function(){
      var initialText = textarea.value || '';
      var languageSelect = document.getElementById('snippetLanguage');
      function mapLang(val){
        if(!val) return 'plaintext';
        var m = val.toLowerCase();
        if(m==='python') return 'python';
        if(m==='javascript' || m==='js') return 'javascript';
        if(m==='typescript' || m==='ts') return 'typescript';
        if(m==='html') return 'html';
        if(m==='css') return 'css';
        if(m==='bash' || m==='sh') return 'shell';
        if(m==='json') return 'json';
        return 'plaintext';
      }

      var editor = monaco.editor.create(editorDiv, {
        value: initialText,
        language: mapLang(languageSelect && languageSelect.value),
        theme: 'vs-dark',
        automaticLayout: true,
        minimap: {enabled:false},
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 13,
        tabSize: 2,
        scrollBeyondLastLine: false
      });

      // wire language changes
      if(languageSelect){
        languageSelect.addEventListener('change', function(){
          var lang = mapLang(languageSelect.value);
          monaco.editor.setModelLanguage(editor.getModel(), lang);
          document.getElementById('csStatusLang').textContent = languageSelect.options[languageSelect.selectedIndex].text || languageSelect.value;
        });
      }

      // update status (line/col)
      editor.onDidChangeCursorPosition(function(e){
        try{ var pos = e.position; document.getElementById('csStatusLn').textContent = 'Ln '+pos.lineNumber+', Col '+pos.column; }catch(e){}
      });

      // Keybindings: Ctrl+S -> Save; Ctrl+Enter -> Run
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KEY_S, function(){
        // copy back to textarea before saving to keep fallback in sync
        textarea.value = editor.getValue();
        var saveBtn = document.getElementById('btnSaveSnippet'); if(saveBtn) saveBtn.click();
      });
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, function(){
        textarea.value = editor.getValue();
        var runBtn = document.getElementById('btnRunSnippet'); if(runBtn) runBtn.click();
      });

      // Show editor when Code Studio tab is active (the page makes tab active by class)
      function showEditorIfNeeded(){
        var codeTab = document.getElementById('tab-code');
        if(codeTab && codeTab.classList.contains('dash-tab-content')){
          editorDiv.style.display = '';
          textarea.style.display = 'none';
          editor.layout();
        } else {
          editorDiv.style.display = 'none';
          textarea.style.display = 'none';
        }
      }

      // initial show
      editorDiv.style.display = '';
      textarea.style.display = 'none';
      editor.layout();

      // Ensure content syncs back on form submission or save
      var saveBtn = document.getElementById('btnSaveSnippet');
      if(saveBtn){
        saveBtn.addEventListener('click', function(){ textarea.value = editor.getValue(); });
      }

      // Expose a small API
      window._codenestEditor = { getValue: function(){ return editor.getValue(); }, setValue: function(v){ editor.setValue(v); }, editor: editor };

    });
  };
  document.head.appendChild(loaderScript);
})();
