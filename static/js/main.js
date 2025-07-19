document.addEventListener("DOMContentLoaded", function () {
    const studentTableBlock = document.getElementById('student-table');
    const analysisBlock = document.getElementById('student-analysis');
    const outputBlock = document.getElementById('output');
    const form = document.getElementById('analysis-form');
    const motivatedForm = document.getElementById('motivated-form');
    const motivatedResults = document.getElementById('motivated-results');
    const preloader = document.getElementById('preloader');

    function showLoader() {
        if (preloader) preloader.style.display = 'block';
    }

    function hideLoader() {
        if (preloader) preloader.style.display = 'none';
    }

    async function sendRequest(path, data, method = 'POST') {
        const response = await fetch(`${API_BASE_URL}/${path}`, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        return await response.json();
    }

    // Tab switching
    document.querySelectorAll('#analysisTabs .nav-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelectorAll('#analysisTabs .nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            document.querySelectorAll('.tab-pane').forEach(pane => pane.style.display = 'none');
            const targetTab = link.getAttribute('data-tab');
            document.getElementById(targetTab).style.display = 'block';

            if (targetTab === 'tab-all-students') {
                fetchStudents(1);
            }
        });
    });

    // Load student table
    window.fetchStudents = async function (page = 1) {
        showLoader();
        analysisBlock.innerHTML = '';
        studentTableBlock.innerHTML = '';
        const response = await fetch(`${API_BASE_URL}/students?page=${page}`);
        studentTableBlock.innerHTML = await response.text();
        hideLoader();
    };

    // Analysis per student (from table)
    window.showAnalysis = async function (email) {
        showLoader();
        const weekFrom = document.getElementById('week_from').value;
        const weekTo = document.getElementById('week_to').value;
        const action = 'analyse_student';
        analysisBlock.innerHTML = '';

        const payload = {
            action,
            email,
            week_from: weekFrom,
            week_to: weekTo,
            num_students: 1
        };

        const data = await sendRequest('analysis', payload);
        if (data.html) {
            analysisBlock.innerHTML = data.html;
        } else {
            analysisBlock.innerHTML = `<p class="text-danger">${data.error || 'Unknown error'}</p>`;
        }
        hideLoader();
    };

    // Check by student form
    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();

            showLoader();
            outputBlock.innerHTML = '';
            const formData = new FormData(form);
            const payload = {
                action: formData.get('action'),
                email: formData.get('email'),
                week_from: formData.get('week_from'),
                week_to: formData.get('week_to'),
                num_students: 1
            };

            const data = await sendRequest('analysis', payload);
            if (data.html) {
                outputBlock.innerHTML = data.html;
            } else {
                outputBlock.innerHTML = `<p class="text-danger">${data.error || 'Unknown error'}</p>`;
            }
            hideLoader();
        });
    }

    // Motivated Students form
    if (motivatedForm) {
        motivatedForm.addEventListener("submit", async function (e) {
            e.preventDefault();

            showLoader();
            motivatedResults.innerHTML = '';

            const type = document.getElementById('motivated-type').value;
            const number = document.getElementById('motivated-number').value;
            const weekFrom = document.getElementById('motivated-week-from').value;
            const weekTo = document.getElementById('motivated-week-to').value;
            const studentEmail = document.getElementById('student-email').value;

            const payload = {
                action: type,
                week_from: weekFrom,
                week_to: weekTo,
                email: studentEmail,
                num_students: number
            };

            const data = await sendRequest('analysis', payload);
            if (data.html) {
                motivatedResults.innerHTML = data.html;
            } else {
                motivatedResults.innerHTML = `<p class="text-danger">${data.error || 'Unknown error'}</p>`;
            }

            hideLoader();
        });
    }

    // Auto-load default tab
    document.querySelector('#analysisTabs .nav-link.active').click();

    // Autocomplete logic
    let autocompleteTimeout = null;
    let preventSearch = false;
    const emailInput = document.getElementById('student-email');
    const resultBox = document.getElementById('autocomplete-results');

    if (emailInput) {
        emailInput.addEventListener('input', function () {
            if (preventSearch) return;

            clearTimeout(autocompleteTimeout);
            const query = this.value.trim();
            if (query.length < 2) {
                resultBox.innerHTML = '';
                return;
            }

            autocompleteTimeout = setTimeout(async () => {
                try {
                    const res = await fetch(`${API_BASE_URL}/search-students?q=${encodeURIComponent(query)}`);
                    const emails = await res.json();

                    resultBox.innerHTML = '';
                    emails.forEach(email => {
                        const item = document.createElement('a');
                        item.href = '#';
                        item.className = 'list-group-item list-group-item-action';
                        item.textContent = email;
                        item.onclick = (e) => {
                            e.preventDefault();
                            preventSearch = true;
                            emailInput.value = email;
                            resultBox.innerHTML = '';
                            showAnalysis(email);
                            preventSearch = false
                        };
                        resultBox.appendChild(item);
                    });
                } catch (error) {
                    console.error("Autocomplete fetch error:", error);
                    resultBox.innerHTML = '<div class="text-danger px-2">Failed to fetch results</div>';
                }
            }, 500);
        });
    }

    const clearButton = document.getElementById('clear-student');
    if (clearButton && emailInput) {
        clearButton.addEventListener('click', () => {
            emailInput.value = '';
            resultBox.innerHTML = '';
            analysisBlock.innerHTML = '';
        });
    }
});