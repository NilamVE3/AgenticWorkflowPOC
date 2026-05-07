// Integration Platform UI JavaScript - Clean Version
class IntegrationPlatformUI {
    constructor() {
        this.baseURL = 'http://localhost:8000';
        this.token = localStorage.getItem('auth_token');
        this.currentPage = 'dashboard';
        this.connectors = {
            slack: { status: 'disconnected', tools: [] },
            http: { status: 'disconnected', tools: [] },
            gmail: { status: 'disconnected', tools: [] },
            github: { status: 'disconnected', tools: [] }
        };
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.checkAuth();
    }

    async checkAuth() {
        if (!this.token) {
            this.showLogin();
            return;
        }

        try {
            // Call an endpoint that requires authentication to validate the token
            const response = await this.apiCall('/api/auth/credentials');
            // If we get here, auth is successful
            console.log('Auth check successful');
            await this.loadDashboard();
        } catch (error) {
            console.error('Auth check failed:', error);
            this.logout();
        }
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (this.token) {
            options.headers['Authorization'] = `Bearer ${this.token}`;
        }

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`${this.baseURL}${endpoint}`, options);
        
        if (!response.ok) {
            console.error(`API Error: ${response.status} ${response.statusText}`);
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    async loadDashboard() {
        try {
            const [systemInfo, tools, connectors] = await Promise.all([
                this.apiCall('/api/system/info'),
                this.apiCall('/api/tools'),
                this.apiCall('/api/connectors')
            ]);

            // Update connector status based on available connectors
            this.updateConnectorStatus(connectors);
            this.renderDashboard(systemInfo, tools, connectors, []);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    updateConnectorStatus(connectors) {
        // Update connector status from API response
        if (connectors && connectors.connectors) {
            Object.entries(connectors.connectors).forEach(([connector, config]) => {
                if (this.connectors[connector]) {
                    this.connectors[connector].status = config.status;
                    this.connectors[connector].config = config;
                }
            });
        }
    }

    renderConnectorManagement() {
        return Object.entries(this.connectors).map(([connector, config]) => `
            <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <span style="font-weight: bold; font-size: 1.1rem; color: #1e293b;">${connector.toUpperCase()}</span>
                        <span style="margin-left: 10px; background: ${config.status === 'connected' ? '#10b981' : '#ef4444'}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">
                            ${config.status === 'connected' ? 'Connected' : 'Not Connected'}
                        </span>
                    </div>
                    <button class="btn" onclick="app.configureConnector('${connector}')">Configure</button>
                </div>
                <div style="color: #64748b; font-size: 0.9rem;">
                    ${config.status === 'connected' ? `${config.tools?.length || 0} tools available` : 'Click Configure to connect'}
                </div>
            </div>
        `).join('');
    }

    renderConnectorsAndTools(tools) {
        if (!tools || !tools.tools || tools.tools.length === 0) {
            return '<p>No tools available</p>';
        }

        // Group tools by connector
        const toolsByConnector = {};
        tools.tools.forEach(tool => {
            const connector = tool.connector_name || 'Unknown';
            if (!toolsByConnector[connector]) {
                toolsByConnector[connector] = [];
            }
            toolsByConnector[connector].push(tool);
        });

        // Render connectors and their tools
        return Object.entries(toolsByConnector).map(([connector, connectorTools]) => `
            <div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e5e7eb; border-radius: 8px;">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <span style="font-weight: bold; font-size: 1.1rem; color: #1e293b;">${connector.toUpperCase()}</span>
                    <span style="margin-left: 10px; background: #667eea; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">
                        ${connectorTools.length} tools
                    </span>
                </div>
                <div style="display: grid; gap: 8px;">
                    ${connectorTools.map(tool => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f8f9fa; border-radius: 6px; cursor: pointer;" onclick="app.executeTool('${tool.id}')">
                            <div>
                                <span style="font-weight: 500; color: #374151;">${tool.name}</span>
                                <span style="margin-left: 8px; color: #64748b; font-size: 0.9rem;">${tool.category}</span>
                            </div>
                            <button class="btn" style="padding: 4px 8px; font-size: 0.8rem;" onclick="event.stopPropagation(); app.executeTool('${tool.id}')">Execute</button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    renderDashboard(systemInfo, tools, workflows, executions) {
        const container = document.getElementById('app');
        container.innerHTML = `
            <div class="container">
                <div class="header">
                    <h1>Integration Platform</h1>
                    <p>Scalable integration platform with 1000+ connectors</p>
                    <button class="btn secondary" onclick="app.logout()">Logout</button>
                </div>

                <div class="dashboard">
                    <div class="card">
                        <h3><span class="status-indicator"></span> System Status</h3>
                        <div class="metric">
                            <span class="metric-label">Total Tools</span>
                            <span class="metric-value">${tools.tools ? tools.tools.length : 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Active Workflows</span>
                            <span class="metric-value">${workflows.workflows ? workflows.workflows.length : 0}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Running Executions</span>
                            <span class="metric-value">${systemInfo.components?.workflows?.running || 0}</span>
                        </div>
                    </div>

                    <div class="card">
                        <h3>Connector Management</h3>
                        <div class="connector-list">
                            ${this.renderConnectorManagement()}
                        </div>
                    </div>

                    <div class="card">
                        <h3>Available Tools</h3>
                        <div class="connector-list">
                            ${this.renderConnectorsAndTools(tools)}
                        </div>
                    </div>

                    <div class="card">
                        <h3>Quick Actions</h3>
                        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                            <button class="btn" onclick="app.showCreateWorkflow()">Create Workflow</button>
                            <button class="btn" onclick="app.showTools()">Browse Tools</button>
                            <button class="btn" onclick="app.showAgentChat()">AI Assistant</button>
                        </div>
                    </div>

                    <div class="card">
                        <h3>Recent Workflows</h3>
                        <div class="workflow-list">
                            ${workflows.workflows?.slice(0, 5).map(workflow => `
                                <div class="workflow-item" onclick="app.viewWorkflow('${workflow.id}')">
                                    <div class="workflow-header">
                                        <span class="workflow-name">${workflow.name}</span>
                                        <span class="workflow-status ${workflow.status || 'active'}">${workflow.status || 'Active'}</span>
                                    </div>
                                    <p>${workflow.description || 'No description'}</p>
                                </div>
                            `).join('') || '<p>No workflows found</p>'}
                        </div>
                    </div>

                    <div class="card">
                        <h3>Recent Executions</h3>
                        <div>
                            ${executions.slice(0, 5).map(execution => `
                                <div style="padding: 10px; border-bottom: 1px solid #e5e7eb;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span><strong>${execution.workflow_name || 'Unknown'}</strong></span>
                                        <span class="workflow-status ${execution.status || 'completed'}">${execution.status || 'Completed'}</span>
                                    </div>
                                    <small style="color: #64748b;">${new Date(execution.started_at).toLocaleString()}</small>
                                </div>
                            `).join('') || '<p>No recent executions</p>'}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async showCreateWorkflow() {
        const modal = this.createModal('Create Workflow', `
            <form id="workflow-form">
                <div class="form-group">
                    <label>Workflow Name</label>
                    <input type="text" id="workflow-name" required>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea id="workflow-description" rows="3"></textarea>
                </div>
                <div class="form-group">
                    <label>Trigger Type</label>
                    <select id="trigger-type">
                        <option value="webhook">Webhook</option>
                        <option value="scheduled">Scheduled</option>
                        <option value="manual">Manual</option>
                    </select>
                </div>
                <button type="submit" class="btn">Create Workflow</button>
            </form>
        `);

        modal.querySelector('#workflow-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.createWorkflow(modal);
        });
    }

    async createWorkflow(modal) {
        const name = modal.querySelector('#workflow-name').value;
        const description = modal.querySelector('#workflow-description').value;
        const triggerType = modal.querySelector('#trigger-type').value;

        try {
            const response = await this.apiCall('/api/workflows', 'POST', {
                name: name,
                description: description,
                steps: [],
                trigger: { type: triggerType }
            });

            if (response.workflow_id) {
                this.showSuccess('Workflow created successfully!');
                this.closeModal(modal);
                await this.loadDashboard();
            } else {
                this.showError('Failed to create workflow');
            }
        } catch (error) {
            console.error('Create workflow failed:', error);
            this.showError('Failed to create workflow');
        }
    }

    async showTools() {
        try {
            const tools = await this.apiCall('/api/tools');
            
            const modal = this.createModal('Available Tools', `
                <div class="tool-list">
                    ${tools.tools?.map(tool => `
                        <div class="workflow-item" onclick="app.executeTool('${tool.id}')">
                            <div class="workflow-header">
                                <span class="workflow-name">${tool.name}</span>
                                <span class="workflow-status active">${tool.category || 'General'}</span>
                            </div>
                            <p>${tool.description}</p>
                        </div>
                    `).join('') || '<p>No tools found</p>'}
                </div>
            `);
        } catch (error) {
            console.error('Failed to load tools:', error);
            this.showError('Failed to load tools');
        }
    }

    configureConnector(connectorType) {
        const modal = this.createModal(`Configure ${connectorType.toUpperCase()} Connector`, this.getConnectorConfigForm(connectorType));
        
        // Add form submission handler
        const form = modal.querySelector('form');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.saveConnectorConfig(connectorType, modal);
            });
        }
    }

    getConnectorConfigForm(connectorType) {
        switch (connectorType) {
            case 'slack':
                return `
                    <form id="connector-form">
                        <div class="form-group">
                            <label>Bot Token</label>
                            <input type="password" id="bot-token" placeholder="xoxb-your-slack-bot-token" required>
                            <small style="color: #64748b;">Get this from your Slack app settings</small>
                        </div>
                        <div class="form-group">
                            <label>Workspace Name</label>
                            <input type="text" id="workspace" placeholder="your-workspace">
                        </div>
                        <button type="submit" class="btn">Test Connection</button>
                        <button type="button" class="btn secondary" onclick="app.closeModal(this.closest('.modal'))">Cancel</button>
                    </form>
                `;
                
            case 'http':
                return `
                    <form id="connector-form">
                        <div class="form-group">
                            <label>Base URL</label>
                            <input type="url" id="base-url" placeholder="https://api.example.com" required>
                        </div>
                        <div class="form-group">
                            <label>API Key (Optional)</label>
                            <input type="password" id="api-key" placeholder="Your API key">
                        </div>
                        <button type="submit" class="btn">Test Connection</button>
                        <button type="button" class="btn secondary" onclick="app.closeModal(this.closest('.modal'))">Cancel</button>
                    </form>
                `;
                
            default:
                return `<p>Connector configuration for ${connectorType} coming soon!</p>`;
        }
    }

    async saveConnectorConfig(connectorType, modal) {
        try {
            const form = modal.querySelector('form');
            const formData = new FormData(form);
            const config = Object.fromEntries(formData.entries());
            
            // Call backend API to configure connector
            const response = await this.apiCall('/api/connectors/configure', 'POST', {
                connector_type: connectorType,
                config: config
            });

            if (response.success) {
                this.showSuccess(`${connectorType.toUpperCase()} connector configured successfully!`);
                this.closeModal(modal);
                
                // Refresh dashboard to show updated status
                await this.loadDashboard();
            } else {
                this.showError('Configuration failed: ' + (response.error || 'Unknown error'));
            }
            
        } catch (error) {
            console.error('Connector configuration failed:', error);
            this.showError('Failed to configure connector');
        }
    }

    async executeTool(toolId) {
        const modal = this.createModal('Execute Tool', `
            <form id="tool-form">
                <div class="form-group">
                    <label>Parameters (JSON)</label>
                    <textarea id="tool-parameters" rows="5" placeholder='{"key": "value"}'></textarea>
                </div>
                <button type="submit" class="btn">Execute Tool</button>
            </form>
        `);

        modal.querySelector('#tool-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.runTool(toolId, modal);
        });
    }

    async runTool(toolId, modal) {
        const parametersText = modal.querySelector('#tool-parameters').value;
        let parameters = {};
        
        try {
            if (parametersText.trim()) {
                parameters = JSON.parse(parametersText);
            }
        } catch (error) {
            this.showError('Invalid JSON parameters');
            return;
        }

        try {
            const response = await this.apiCall('/api/tools/execute', 'POST', {
                tool_id: toolId,
                parameters: parameters
            });

            if (response.success) {
                this.showSuccess('Tool executed successfully!');
                this.closeModal(modal);
                this.showResult('Tool Result', response.result);
            } else {
                this.showError('Tool execution failed');
            }
        } catch (error) {
            console.error('Tool execution failed:', error);
            this.showError('Tool execution failed');
        }
    }

    async showAgentChat() {
        const modal = this.createModal('AI Assistant', `
            <div style="height: 400px; display: flex; flex-direction: column;">
                <div style="flex: 1; overflow-y: auto; padding: 10px; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 10px;" id="chat-history">
                    <div style="background: #f3f4f6; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                        <p style="margin: 0; color: #9ca3af;">🤖 Hello! I can help you create workflows and execute tools. What would you like to do?</p>
                    </div>
                </div>
                <form id="agent-form" style="display: flex; gap: 10px;">
                    <input type="text" id="agent-prompt" placeholder="Ask me to create a workflow or execute tools..." style="flex: 1; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px;">
                    <button type="submit" class="btn">Send</button>
                </form>
            </div>
        `);

        modal.querySelector('#agent-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.chatWithAgent(modal);
        });
    }

    async chatWithAgent(modal) {
        const prompt = modal.querySelector('#agent-prompt').value;
        const chatHistory = modal.querySelector('#chat-history');

        if (!prompt.trim()) return;

        // Add user message
        chatHistory.innerHTML += `
            <div style="background: #e5e7eb; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                <strong>You:</strong> ${prompt}
            </div>
        `;

        try {
            const response = await this.apiCall('/api/agent/chat', 'POST', {
                prompt: prompt,
                capabilities: ['workflow_generation', 'tool_selection']
            });

            // Add agent response
            chatHistory.innerHTML += `
                <div style="background: #f3f4f6; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                    <strong>🤖 Assistant:</strong> ${response.response || 'I apologize, but I could not process that request.'}
                </div>
            `;

            // Scroll to bottom
            chatHistory.scrollTop = chatHistory.scrollHeight;

            // Clear input
            modal.querySelector('#agent-prompt').value = '';

            // Execute tool calls if any
            if (response.tool_calls && response.tool_calls.length > 0) {
                for (const toolCall of response.tool_calls) {
                    await this.runTool(toolCall.tool_id, modal);
                }
            }

        } catch (error) {
            console.error('Agent chat failed:', error);
            chatHistory.innerHTML += `
                <div style="background: #fef2f2; padding: 10px; border-radius: 6px; margin-bottom: 10px; color: #dc2626;">
                    <strong>🤖 Error:</strong> Failed to get response from AI assistant
                </div>
            `;
        }
    }

    async viewWorkflow(workflowId) {
        try {
            const workflow = await this.apiCall(`/api/workflows/${workflowId}`);
            
            const modal = this.createModal('Workflow Details', `
                <div>
                    <h3>${workflow.name}</h3>
                    <p>${workflow.description || 'No description'}</p>
                    <div style="margin-top: 20px;">
                        <button class="btn" onclick="app.executeWorkflow('${workflowId}')">Execute Workflow</button>
                        <button class="btn secondary" onclick="app.closeModal(this.closest('.modal'))">Close</button>
                    </div>
                </div>
            `);
        } catch (error) {
            console.error('Failed to load workflow:', error);
            this.showError('Failed to load workflow');
        }
    }

    async executeWorkflow(workflowId) {
        try {
            const response = await this.apiCall(`/api/workflows/${workflowId}/execute`, 'POST');
            
            if (response.execution_id) {
                this.showSuccess('Workflow execution started!');
                this.closeModal(document.querySelector('.modal'));
            } else {
                this.showError('Failed to execute workflow');
            }
        } catch (error) {
            console.error('Workflow execution failed:', error);
            this.showError('Failed to execute workflow');
        }
    }

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" onclick="app.closeModal(this.closest('.modal'))">&times;</button>
                </div>
                ${content}
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }

    closeModal(modal) {
        if (modal) {
            modal.remove();
        } else {
            document.querySelectorAll('.modal').forEach(m => m.remove());
        }
    }

    showResult(title, result) {
        const modal = this.createModal(title, `
            <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; font-family: monospace; white-space: pre-wrap; overflow-x: auto;">
                ${JSON.stringify(result, null, 2)}
            </div>
            <div style="margin-top: 15px; text-align: center;">
                <button class="btn" onclick="app.closeModal(this.closest('.modal'))">Close</button>
            </div>
        `);
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            max-width: 300px;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    logout() {
        localStorage.removeItem('auth_token');
        window.location.reload();
    }

    setupEventListeners() {
        // Handle navigation
        window.addEventListener('hashchange', () => {
            const hash = window.location.hash.slice(1);
            if (hash && hash !== this.currentPage) {
                this.currentPage = hash;
                this.handleRoute();
            }
        });

        // Initial route handling
        if (window.location.hash) {
            this.currentPage = window.location.hash.slice(1);
            this.handleRoute();
        }
    }

    handleRoute() {
        switch (this.currentPage) {
            case 'login':
                this.showLogin();
                break;
            default:
                this.loadDashboard();
                break;
        }
    }

    showLogin() {
        const container = document.getElementById('app');
        container.innerHTML = `
            <div class="container" style="margin-top: 100px;">
                <div class="header" style="max-width: 400px; margin: 0 auto;">
                    <h1>Login</h1>
                    <p>Access the Integration Platform</p>
                </div>
                <div class="card" style="max-width: 400px; margin: 0 auto;">
                    <form id="login-form">
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="username" required>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="password" required>
                        </div>
                        <button type="submit" class="btn" style="width: 100%;">Login</button>
                    </form>
                </div>
            </div>
        `;

        document.querySelector('#login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.login();
        });
    }

    async login() {
        const username = document.querySelector('#username').value;
        const password = document.querySelector('#password').value;

        try {
            const response = await this.apiCall('/api/auth/login', 'POST', {
                username: username,
                password: password
            });

            if (response.access_token) {
                this.token = response.access_token;
                localStorage.setItem('auth_token', response.access_token);
                window.location.hash = '';
                await this.loadDashboard();
            } else {
                this.showError('Login failed');
            }
        } catch (error) {
            console.error('Login failed:', error);
            this.showError('Login failed');
        }
    }
}

// Initialize the application
const app = new IntegrationPlatformUI();
