/**
 * Upload page interactivity — progressive enhancement only.
 * Real validation & progress live server-side; this just looks nice.
 */
(function () {
    'use strict';

    var MAX_SIZE = 5 * 1024 * 1024;
    var ALLOWED = { '.csv': true, '.xlsx': true };

    function $(id) { return document.getElementById(id); }

    document.addEventListener('DOMContentLoaded', function () {
        var dropZone = $('drop-zone');
        var fileInput = $('id_file');
        var dzInner = $('dz-inner');
        var dzFile = $('dz-file');
        var dzFileName = $('dz-file-name');
        var dzFileSize = $('dz-file-size');
        var dzRemove = $('dz-remove');
        var preview = $('file-preview');
        var templateCard = $('template-card');
        var uploadBtn = $('upload-btn');
        var form = $('upload-form');
        var progressWrap = $('upload-progress');
        var progressBar = $('progress-bar');
        var progressPct = $('progress-pct');
        var progressNote = $('progress-note');
        var dropStyle = document.querySelector('style[data-dropzone]');

        if (!dropZone || !fileInput) return;

        /* ---------- Dropzone CSS (injected once) ---------- */
        if (!dropStyle) {
            var style = document.createElement('style');
            style.dataset.dropzone = '1';
            style.textContent =
                '.drop-zone{' +
                '  border:2px dashed #c3ccd6;' +
                '  border-radius:1rem;' +
                '  background:#fafcff;' +
                '  padding:2.2rem 1.5rem;' +
                '  text-align:center;' +
                '  cursor:pointer;' +
                '  transition:border-color .2s ease, background .2s ease, transform .2s ease, box-shadow .2s ease;' +
                '  outline:none;' +
                '}' +
                '.drop-zone:hover{ border-color:#0d6efd; background:#f2f7ff; }' +
                '.drop-zone:focus-visible{ box-shadow:0 0 0 4px rgba(13,110,253,.18); }' +
                '.drop-zone.dragover{ border-color:#0d6efd; background:#e9f2ff; transform:scale(1.01); box-shadow:0 8px 30px rgba(13,110,253,.15); }' +
                '.drop-zone.dragover .dz-icon i{ transform:translateY(-4px); }' +
                '.drop-zone.has-file{ border-style:solid; border-color:#198754; background:#f2fdf6; padding:1rem 1.25rem; cursor:default; }' +
                '.drop-zone .dz-icon{ font-size:3rem; color:#0d6efd; transition:transform .2s ease; }' +
                '.dz-icon i{ display:inline-block; transition:transform .2s ease; }' +
                '.dz-title{ font-weight:700; font-size:1.05rem; color:#1d2b3a; margin-top:.25rem; }' +
                '.dz-sub{ color:#6c757d; font-size:.9rem; }' +
                '.dz-formats{ }' +
                '.dz-file{ display:none; align-items:center; gap:1rem; text-align:left; }' +
                '.drop-zone.has-file .dz-file{ display:flex; }' +
                '.drop-zone.has-file .dz-inner{ display:none; }' +
                '.dz-file-icon{ font-size:2.2rem; color:#198754; flex-shrink:0; }' +
                '.dz-file-name{ font-weight:600; color:#1d2b3a; }' +
                '.dz-file-size{ color:#6c757d; font-size:.85rem; }' +
                '.dz-file .btn-close{ margin-left:auto; flex-shrink:0; }';

            document.head.appendChild(style);
        }

        /* ---------- shared helpers ---------- */
        function setError(message) {
            preview.innerHTML =
                '<i class="bi bi-exclamation-circle text-danger me-1"></i>' +
                '<span class="text-danger">' + message + '</span>';
            dropZone.classList.remove('has-file');
            dzFile.classList.add('d-none');
            fileInput.value = '';
            uploadBtn.disabled = true;
            UPLOADED_FILE = null;
        }

        function clearPreview() {
            preview.innerHTML = '';
        }

        function formatBytes(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }

        function extOf(name) {
            var idx = String(name).lastIndexOf('.');
            return idx === -1 ? '' : String(name).slice(idx).toLowerCase();
        }

        var UPLOADED_FILE = null;

        function loadFile(file) {
            if (!file) return;
            var ext = extOf(file.name);
            if (!ALLOWED[ext]) {
                setError('Unsupported file type. Only .csv and .xlsx files are allowed.');
                window.showToast && window.showToast('Only .csv and .xlsx allowed', 'warning');
                return;
            }
            if (file.size === 0) {
                setError('The uploaded file is empty.');
                return;
            }
            if (file.size > MAX_SIZE) {
                setError('File is too large. Maximum allowed size is 5 MB.');
                window.showToast && window.showToast('File too large (max 5 MB)', 'warning');
                return;
            }

            UPLOADED_FILE = file;
            dzFileName.textContent = file.name;
            dzFileSize.textContent = formatBytes(file.size);
            dropZone.classList.add('has-file');
            dzFile.classList.remove('d-none');
            uploadBtn.disabled = false;
            templateCard && templateCard.classList.remove('d-none');
            clearPreview();

            /* reassign file for HTML5 submission fidelity is tricky:
               we keep the input in sync instead for compat with old browsers
               (FileList can't be appended to in old browsers).
               The input value can't be set programmatically, so we let the
               user's real input hold the file — see picker below. */

            // Give the input the file via DataTransfer (modern browsers).
            if (window.DataTransfer) {
                try {
                    var dt = new DataTransfer();
                    dt.items.add(file);
                    fileInput.files = dt.files;
                } catch (e) { /* fall back to native picker on submit */ }
            }
        }

        /* ---------- click to browse ---------- */
        dropZone.addEventListener('click', function (e) {
            // Don't reopen the picker when clicking the remove button.
            if (e.target.closest('.btn-close') || dropZone.classList.contains('has-file')) return;
            fileInput.click();
        });
        dropZone.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });

        /* ---------- native picker ---------- */
        fileInput.addEventListener('change', function () {
            var f = fileInput.files && fileInput.files[0];
            if (f) {
                loadFile(f);
            } else {
                resetAll();
            }
        });

        /* ---------- remove selected file ---------- */
        dzRemove.addEventListener('click', function (e) {
            e.stopPropagation();
            if (window.DataTransfer) {
                try {
                    var dt = new DataTransfer();
                    fileInput.files = dt.files;
                } catch (err) { /* ignore */ }
            }
            resetAll();
        });

        function resetAll() {
            UPLOADED_FILE = null;
            dropZone.classList.remove('has-file');
            dzFile.classList.add('d-none');
            uploadBtn.disabled = true;
            templateCard && templateCard.classList.add('d-none');
            clearPreview();
        }

        /* ---------- drag & drop ---------- */
        ['dragenter', 'dragover'].forEach(function (evt) {
            dropZone.addEventListener(evt, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            });
        });
        ['dragleave', 'drop'].forEach(function (evt) {
            dropZone.addEventListener(evt, function (e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            });
        });
        dropZone.addEventListener('drop', function (e) {
            var files = e.dataTransfer && e.dataTransfer.files;
            if (files && files.length) loadFile(files[0]);
        });
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function (evt) {
            window.addEventListener(evt, function (e) {
                e.preventDefault();
            });
        });

        /* ---------- fake upload progress ---------- */
        var progressTimer = null;
        form.addEventListener('submit', function (e) {
            // Client-side guard (server is the source of truth).
            if (!UPLOADED_FILE && !(fileInput.files && fileInput.files[0])) {
                e.preventDefault();
                setError('Please choose a file to upload.');
                return;
            }

            // If the DataTransfer fallback failed, we have a real file in the
            // input already — proceed normally.
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<i class="bi bi-arrow-repeat me-1 upload-spin"></i> Importing…';

            progressWrap.classList.remove('d-none');
            progressBar.style.width = '0%';
            progressPct.textContent = '0%';
            startProgress();
        });

        function startProgress() {
            var pct = 0;
            clearInterval(progressTimer);
            progressTimer = setInterval(function () {
                // Slower near the end to feel like real work.
                pct += pct < 60 ? 7 : pct < 85 ? 3 : 1;
                if (pct >= 99) {
                    pct = 99;              // stay shy of 100% until redirect
                    clearInterval(progressTimer);
                    progressNote.textContent = 'Almost done — preparing your results…';
                }
                progressBar.style.width = pct + '%';
                progressPct.textContent = Math.round(pct) + '%';
            }, 220);
        }
    });
})();