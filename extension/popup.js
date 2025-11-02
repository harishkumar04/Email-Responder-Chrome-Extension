// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

// DOM Elements
const emailInput = document.getElementById('emailInput');
const responseType = document.getElementById('responseType');
const generateBtn = document.getElementById('generateBtn');
const loadingSection = document.getElementById('loadingSection');
const errorSection = document.getElementById('errorSection');
const responseSection = document.getElementById('responseSection');
const responseText = document.getElementById('responseText');
const copyBtn = document.getElementById('copyBtn');
const suggestions = document.getElementById('suggestions');

// Event Listeners
generateBtn.addEventListener('click', generateResponse);
copyBtn.addEventListener('click', copyResponse);

// Load saved data when popup opens
document.addEventListener('DOMContentLoaded', function() {
    loadSavedData();
    checkGmailTab();
});

// Check if we're on Gmail and try to extract email content
async function checkGmailTab() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab.url && tab.url.includes('mail.google.com')) {
            // Try to get email content from the page
            chrome.tabs.sendMessage(tab.id, { action: 'getEmailContent' }, (response) => {
                if (response && response.emailContent) {
                    emailInput.value = response.emailContent;
                    saveData();
                }
            });
        }
    } catch (error) {
        console.log('Not on Gmail or unable to access tab');
    }
}

// Generate email response
async function generateResponse() {
    const email = emailInput.value.trim();
    
    if (!email) {
        showError('Please enter an email to respond to');
        return;
    }

    // Show loading state
    generateBtn.disabled = true;
    generateBtn.textContent = 'Generating...';
    loadingSection.style.display = 'block';
    errorSection.style.display = 'none';
    responseSection.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/generate-response`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email_content: email,
                response_type: responseType.value
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResponse(data);
        saveData();

    } catch (error) {
        console.error('Error generating response:', error);
        showError('Failed to generate response. Make sure the backend server is running on localhost:8000');
    } finally {
        // Reset button state
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Response';
        loadingSection.style.display = 'none';
    }
}

// Display the generated response
function displayResponse(data) {
    responseText.textContent = data.generated_response;
    responseSection.style.display = 'block';
    
    // Clear previous suggestions
    const suggestionsContainer = suggestions;
    const existingSuggestions = suggestionsContainer.querySelectorAll('.suggestion');
    existingSuggestions.forEach(s => s.remove());
    
    // Add new suggestions
    if (data.suggestions && data.suggestions.length > 0) {
        data.suggestions.forEach(suggestion => {
            const suggestionDiv = document.createElement('div');
            suggestionDiv.className = 'suggestion';
            suggestionDiv.textContent = suggestion;
            suggestionDiv.addEventListener('click', () => {
                responseText.textContent = suggestion.replace(/^[^:]+:\s*/, ''); // Remove prefix
            });
            suggestionsContainer.appendChild(suggestionDiv);
        });
    }
}

// Copy response to clipboard
async function copyResponse() {
    try {
        await navigator.clipboard.writeText(responseText.textContent);
        
        // Visual feedback
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.style.backgroundColor = '#1a73e8';
        
        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.backgroundColor = '#34a853';
        }, 2000);
        
    } catch (error) {
        console.error('Failed to copy text:', error);
        showError('Failed to copy to clipboard');
    }
}

// Show error message
function showError(message) {
    errorSection.textContent = message;
    errorSection.style.display = 'block';
    setTimeout(() => {
        errorSection.style.display = 'none';
    }, 5000);
}

// Save data to Chrome storage
function saveData() {
    chrome.storage.local.set({
        emailInput: emailInput.value,
        responseType: responseType.value
    });
}

// Load saved data from Chrome storage
function loadSavedData() {
    chrome.storage.local.get(['emailInput', 'responseType'], (result) => {
        if (result.emailInput) {
            emailInput.value = result.emailInput;
        }
        if (result.responseType) {
            responseType.value = result.responseType;
        }
    });
}

// Utility functions for quick actions
function fillSampleEmail() {
    emailInput.value = `Hi there,

I hope this email finds you well. I wanted to reach out regarding the project we discussed last week. Could we schedule a meeting to go over the details?

I'm available Tuesday and Wednesday afternoon. Please let me know what works best for you.

Best regards,
John Smith`;
    saveData();
}

function clearInput() {
    emailInput.value = '';
    responseSection.style.display = 'none';
    errorSection.style.display = 'none';
    saveData();
}

// Auto-save as user types
emailInput.addEventListener('input', saveData);
responseType.addEventListener('change', saveData);
