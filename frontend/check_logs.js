const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: "new"
    });
    const page = await browser.newPage();

    page.on('console', msg => {
        console.log(`PAGE LOG: [${msg.type()}] ${msg.text()}`);
    });

    page.on('pageerror', error => {
        console.log(`PAGE ERROR: ${error.message}`);
    });

    page.on('requestfailed', request => {
        console.log(`REQUEST FAILED: ${request.url()} - ${request.failure().errorText}`);
    });

    try {
        const response = await page.goto('http://localhost:5173', { waitUntil: 'networkidle0', timeout: 10000 });
        console.log('Page loaded, status:', response.status());
    } catch (e) {
        console.log('Navigation error:', e.message);
    }

    await new Promise(r => setTimeout(r, 5000));
    await browser.close();
})();
