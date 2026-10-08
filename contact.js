// ===== Contact form =====
// Sends the booking request to the Python server, which saves it in a SQLite database.
// If the server isn't running (for example, opening the file directly),
// it falls back to opening the visitor's email app instead.
const form = document.getElementById('contact-form');
const fields = form.elements;            // form.elements.name, not form.name (that's the form's own name)
const statusText = document.getElementById('form-status');
const sendButton = form.querySelector('button');
const MY_EMAIL = 'gitaualice@outlook.com';

// Don't let people pick a date that has already passed
const today = new Date();
today.setMinutes(today.getMinutes() - today.getTimezoneOffset());
fields.shoot_date.min = today.toISOString().slice(0, 10);

function openEmailApp(data) {
    const subject = encodeURIComponent('Photography booking request from ' + data.name);
    const details = 'Type of shoot: ' + data.shoot_type +
        '\nPreferred date: ' + (data.shoot_date || 'not sure yet') +
        '\nLocation: ' + data.location + '\n\n';
    const body = encodeURIComponent(details + data.message + '\n\n— ' + data.name + ' (' + data.email + ')');
    window.location.href = 'mailto:' + MY_EMAIL + '?subject=' + subject + '&body=' + body;
}

form.addEventListener('submit', async e => {
    e.preventDefault();

    const data = {
        name: fields.name.value.trim(),
        email: fields.email.value.trim(),
        message: fields.message.value.trim(),
        shoot_type: fields.shoot_type.value,
        shoot_date: fields.shoot_date.value,
        location: fields.location.value,
        website: fields.website.value          // hidden spam trap
    };

    sendButton.disabled = true;
    statusText.textContent = 'Sending...';

    try {
        const response = await fetch('/api/contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();

        if (result.ok) {
            statusText.textContent = "Thanks, " + data.name + "! I'll get back to you soon.";
            form.reset();
        } else {
            statusText.textContent = result.error;
        }
    } catch (error) {
        // No server available: use the email app instead
        openEmailApp(data);
        statusText.textContent = 'Opening your email app... thanks for reaching out!';
        form.reset();
    } finally {
        sendButton.disabled = false;
    }
});