// Gmail integration - adds button next to Send button
console.log('Email Response Generator: Gmail Send button integration loaded');

const API_BASE_URL = 'http://127.0.0.1:8001';

// Listen for messages from popup (keep existing functionality)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getEmailContent') {
        const emailContent = extractEmailContent();
        sendResponse({ emailContent: emailContent });
    }
});

// Find and add button next to Send buttons
function addButtonsToSendAreas() {
    // Look for Send buttons in Gmail
    const sendButtons = document.querySelectorAll('[data-tooltip="Send ⌘+Enter"], [data-tooltip="Send"], [role="button"][aria-label*="Send"]');
    
    sendButtons.forEach(sendButton => {
        // Check if we already added our button to this send area
        const parentContainer = sendButton.closest('[role="dialog"], .M9, .nH');
        if (parentContainer && !parentContainer.querySelector('.ai-response-btn')) {
            addResponseButtonToSendArea(sendButton);
        }
    });
    
    // Also look for compose toolbars
    const composeToolbars = document.querySelectorAll('.btC, .gU, .J-J5-Ji');
    composeToolbars.forEach(toolbar => {
        if (!toolbar.querySelector('.ai-response-btn')) {
            const sendBtn = toolbar.querySelector('[data-tooltip*="Send"]');
            if (sendBtn) {
                addResponseButtonToSendArea(sendBtn);
            }
        }
    });
}

// Add our response button next to a Send button
function addResponseButtonToSendArea(sendButton) {
    const responseBtn = document.createElement('div');
    responseBtn.className = 'ai-response-btn';
    responseBtn.innerHTML = `
        <div style="
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            margin: 0 8px 0 0;
            background: linear-gradient(135deg, #1a73e8, #4285f4);
            color: white;
            border-radius: 20px;
            cursor: pointer;
            font-size: 13px;
            font-family: 'Google Sans', Roboto, sans-serif;
            font-weight: 500;
            transition: all 0.2s ease;
            user-select: none;
            box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3);
            border: none;
            outline: none;
        " onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 4px 12px rgba(26, 115, 232, 0.4)'" 
           onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 2px 8px rgba(26, 115, 232, 0.3)'">
            <span style="margin-right: 6px; font-size: 14px;">🤖</span>
            <span>AI Response</span>
        </div>
    `;

    // Add click handler
    responseBtn.addEventListener('click', handleResponseButtonClick);
    
    // Insert the button before the Send button
    try {
        const sendContainer = sendButton.parentElement;
        if (sendContainer) {
            sendContainer.insertBefore(responseBtn, sendButton);
            console.log('AI Response button added next to Send button');
        }
    } catch (error) {
        console.log('Could not insert next to Send button, trying alternative placement');
        // Alternative: add to the toolbar container
        const toolbar = sendButton.closest('.btC, .gU, .J-J5-Ji');
        if (toolbar) {
            toolbar.appendChild(responseBtn);
        }
    }
}

// Handle when user clicks the response button
async function handleResponseButtonClick(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const button = event.currentTarget.querySelector('div');
    const originalHTML = button.innerHTML;
    
    try {
        // Show loading state
        button.innerHTML = `
            <span style="margin-right: 6px; font-size: 14px;">⏳</span>
            <span>Generating...</span>
        `;
        button.style.background = 'linear-gradient(135deg, #1557b0, #3367d6)';
        
        // Extract email content from the conversation
        const emailContent = extractEmailContent();
        
        if (!emailContent) {
            throw new Error('No email content found. Please make sure you\'re replying to an email.');
        }

        console.log('Extracted email content:', emailContent.substring(0, 100) + '...');

        // Call API to generate response
        const response = await fetch(`${API_BASE_URL}/generate-response`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email_content: emailContent,
                response_type: 'professional'
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        console.log('Generated response:', data.generated_response);
        
        // Insert the response into the compose area
        const inserted = insertResponseIntoCompose(data.generated_response);
        
        if (inserted) {
            // Show success state
            button.innerHTML = `
                <span style="margin-right: 6px; font-size: 14px;">✅</span>
                <span>Added!</span>
            `;
            button.style.background = 'linear-gradient(135deg, #34a853, #4caf50)';
        } else {
            // Fallback: copy to clipboard
            await navigator.clipboard.writeText(data.generated_response);
            button.innerHTML = `
                <span style="margin-right: 6px; font-size: 14px;">📋</span>
                <span>Copied!</span>
            `;
            button.style.background = 'linear-gradient(135deg, #ff9800, #ffa726)';
        }
        
    } catch (error) {
        console.error('Error generating response:', error);
        
        // Show error state
        button.innerHTML = `
            <span style="margin-right: 6px; font-size: 14px;">❌</span>
            <span>Error</span>
        `;
        button.style.background = 'linear-gradient(135deg, #ea4335, #f44336)';
        
        // Show error details in console
        console.error('Full error:', error.message);
    }
    
    // Reset button after 2.5 seconds
    setTimeout(() => {
        button.innerHTML = originalHTML;
        button.style.background = 'linear-gradient(135deg, #1a73e8, #4285f4)';
    }, 2500);
}

// Insert generated response into Gmail's compose area
function insertResponseIntoCompose(responseText) {
    try {
        // Look for compose areas in the current context
        const composeSelectors = [
            '[contenteditable="true"][aria-label*="Message Body"]',
            '[contenteditable="true"][role="textbox"]',
            '.Am.Al.editable',
            '[g_editable="true"]',
            'div[contenteditable="true"]',
            '[data-tooltip="Message Body"]'
        ];
        
        // Try each selector and find visible compose areas
        for (const selector of composeSelectors) {
            const composeAreas = document.querySelectorAll(selector);
            for (const composeArea of composeAreas) {
                // Check if the compose area is visible and in the current compose window
                if (composeArea.offsetParent !== null && 
                    composeArea.getBoundingClientRect().height > 0) {
                    
                    // Insert the response
                    composeArea.innerHTML = `<div>${responseText}</div><br><br>`;
                    composeArea.focus();
                    
                    // Trigger events to let Gmail know content changed
                    composeArea.dispatchEvent(new Event('input', { bubbles: true }));
                    composeArea.dispatchEvent(new Event('change', { bubbles: true }));
                    composeArea.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                    
                    console.log('Response inserted into compose area');
                    return true;
                }
            }
        }
        
        console.log('No visible compose area found');
        return false;
    } catch (error) {
        console.error('Error inserting into compose:', error);
        return false;
    }
}

// Extract email content from Gmail conversation
function extractEmailContent() {
    try {
        // Multiple selectors for different Gmail layouts and views
        const selectors = [
            '[data-message-id] .ii.gt .a3s.aiL',
            '.ii.gt .a3s.aiL',
            '[role="listitem"] .a3s.aiL',
            '.adn.ads .a3s.aiL',
            '.ii.gt div[dir="ltr"]',
            '[data-legacy-thread-id] .a3s.aiL',
            '.a3s.aiL',
            '.ii.gt'
        ];

        let emailText = '';
        
        // Try each selector to find email content
        for (const selector of selectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                // Get the last email in the conversation (most recent one to reply to)
                const lastEmail = elements[elements.length - 1];
                const text = lastEmail.innerText || lastEmail.textContent;
                if (text && text.trim().length > 20) {
                    emailText = text;
                    break;
                }
            }
        }

        // Fallback: try to get selected text
        if (!emailText || emailText.trim().length < 20) {
            const selection = window.getSelection();
            if (selection.toString().trim().length > 20) {
                emailText = selection.toString().trim();
            }
        }

        // Clean up the email text
        if (emailText) {
            emailText = emailText
                .replace(/\n\s*\n\s*\n/g, '\n\n') // Remove excessive line breaks
                .replace(/^\s+|\s+$/g, '') // Trim whitespace
                .substring(0, 2000); // Limit length
        }

        return emailText;
    } catch (error) {
        console.error('Error extracting email content:', error);
        return '';
    }
}

// Initialize and monitor for new compose windows
function initialize() {
    if (window.location.hostname === 'mail.google.com') {
        console.log('Gmail detected, monitoring for compose windows');
        
        // Initial scan
        setTimeout(() => {
            addButtonsToSendAreas();
        }, 2000);
        
        // Monitor for new compose windows and Gmail navigation
        const observer = new MutationObserver((mutations) => {
            let shouldCheck = false;
            
            mutations.forEach((mutation) => {
                // Check if new nodes were added that might contain compose areas
                if (mutation.addedNodes.length > 0) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Check if it's a compose window or contains Send buttons
                            if (node.querySelector && 
                                (node.querySelector('[data-tooltip*="Send"]') || 
                                 node.classList.contains('M9') ||
                                 node.classList.contains('nH'))) {
                                shouldCheck = true;
                                break;
                            }
                        }
                    }
                }
            });
            
            if (shouldCheck) {
                setTimeout(addButtonsToSendAreas, 500);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Also check periodically for missed compose windows
        setInterval(addButtonsToSendAreas, 5000);
    }
}

// Start when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
