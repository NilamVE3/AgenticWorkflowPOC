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
        await this.checkAuth();
        await this.loadDashboard();
        this.setupEventListeners();
    }

    async checkAuth() {
        if (!this.token) {
            window.location.href = '#login';
            return;
        }

        try {
            const response = await this.apiCall('/api/system/info', 'GET');
            if (!response.ok) {
                this.logout();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
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
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    setupEventListeners() {
        window.addEventListener('hashchange', () => this.handleRoute());
        window.addEventListener('popstate', () => this.handleRoute());
        this.handleRoute();
    }

    handleRoute() {
        const route = window.location.hash.slice(1);
        if (route !== this.currentPage) {
            this.currentPage = route;
            
            switch (route) {
                case 'login':
                    this.showLogin();
                    break;
                case 'dashboard':
                default:
                    this.loadDashboard();
                    break;
            }
        }
    }

    showLogin() {
        const container = document.getElementById('app');
        container.innerHTML = `
            <div class="container">
                <div class="login-form">
                    <h2>Login</h2>
                    <p>Access the Integration Platform</p>
                    <form id="login-form">
                        <div class="form-group">
                            <label>Username</label>
                            <input type="text" id="username" required>
                        </div>
                        <div class="form-group">
                            <label>Password</label>
                            <input type="password" id="password" required>
                        </div>
                        <button type="submit" class="btn">Login</button>
                    </form>
                </div>
            </div>
        `;

        document.getElementById('login-form').addEventListener('submit', async (e) => {
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

    logout() {
        localStorage.removeItem('auth_token');
        this.token = null;
        window.location.hash = 'login';
    }

    async loadDashboard() {
        try {
            const [systemInfo, tools, workflows] = await Promise.all([
                this.apiCall('/api/system/info'),
                this.apiCall('/api/tools'),
                this.apiCall('/api/workflows')
            ]);

            // Update connector status based on available tools
            this.updateConnectorStatus(tools);
            this.renderDashboard(systemInfo, tools, workflows);
        } catch (error) {
            console.error('Failed to load dashboard:', error);
            this.showError('Failed to load dashboard data');
        }
    }

    updateConnectorStatus(tools) {
        // Reset all connectors to disconnected
        Object.keys(this.connectors).forEach(key => {
            this.connectors[key].status = 'disconnected';
            this.connectors[key].tools = [];
        });

        // Update status based on available tools
        if (tools && tools.tools) {
            tools.tools.forEach(tool => {
                const connector = tool.connector_name;
                if (this.connectors[connector]) {
                    this.connectors[connector].status = 'connected';
                    this.connectors[connector].tools.push(tool);
                }
            });
        }
    }

    renderDashboard(systemInfo, tools, workflows) {
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
                </div>
            `;
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
                    ${config.status === 'connected' ? `${config.tools.length} tools available` : 'Click Configure to connect'}
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

    configureConnector(connectorType) {
        const modal = this.createModal(`Configure ${connectorType.toUpperCase()} Connector`, this.getConnectorConfigForm(connectorType));
        
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
                        <button type="submit" class="btn">Save Configuration</button>
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
                        <button type="submit" class="btn">Save Configuration</button>
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
            
            // Save configuration to localStorage for demo
            localStorage.setItem(`connector_${connectorType}_config`, JSON.stringify(config));
            
            // Update connector status
            this.connectors[connectorType].status = 'connected';
            this.connectors[connectorType].config = config;
            
            this.showSuccess(`${connectorType.toUpperCase()} connector configured successfully!`);
            this.closeModal(modal);
            
            // Refresh dashboard to show updated status
            await this.loadDashboard();
            
        } catch (error) {
            console.error('Connector configuration failed:', error);
            this.showError('Failed to configure connector');
        }
    }

    async executeTool(toolId) {
        try {
            // Check if connector is configured
            const tool = await this.getToolById(toolId);
            if (!tool) {
                this.showError('Tool not found');
                return;
            }

            const connector = tool.connector_name;
            if (!this.connectors[connector] || this.connectors[connector].status !== 'connected') {
                this.showError(`Please configure ${connector.toUpperCase()} connector first`);
                return;
            }

            const modal = this.createModal('Execute Tool', `
                <form id="tool-form">
                    <div class="form-group">
                        <label>Tool: ${tool.name}</label>
                        <input type="text" value="${tool.name}" readonly style="background: #f3f4f6;">
                    </div>
                    <div class="form-group">
                        <label>Parameters (JSON)</label>
                        <textarea id="tool-parameters" rows="5" placeholder='{"key": "value"}'></textarea>
                    </div>
                    <button type="submit" class="btn">Execute Tool</button>
                    <button type="button" class="btn secondary" onclick="app.closeModal(this.closest('.modal'))">Cancel</button>
                </form>
            `);

            modal.querySelector('#tool-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.runTool(toolId, modal);
            });
            
        } catch (error) {
            console.error('Tool execution failed:', error);
            this.showError('Failed to execute tool');
        }
    }

    async getToolById(toolId) {
        try {
            const tools = await this.apiCall('/api/tools');
            return tools.tools?.find(tool => tool.id === toolId);
        } catch (error) {
            console.error('Failed to get tool:', error);
            return null;
        }
    }

    async runTool(toolId, modal) {
        try {
            const parametersText = modal.querySelector('#tool-parameters').value;
            let parameters = {};
            
            if (parametersText.trim()) {
                try {
                    parameters = JSON.parse(parametersText);
                } catch (e) {
                    this.showError('Invalid JSON parameters');
                    return;
                }
            }

            const response = await this.apiCall('/api/tools/execute', 'POST', {
                tool_id: toolId,
                parameters: parameters
            });

            if (response.success) {
                this.showSuccess('Tool executed successfully!');
                this.closeModal(modal);
                this.showResult('Tool Result', response.result);
            } else {
                this.showError('Tool execution failed: ' + (response.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Tool execution failed:', error);
            this.showError('Tool execution failed');
        }
    }

    showCreateWorkflow() {
        this.showInfo('Workflow Builder', 'Workflow creation interface coming soon!');
    }

    showTools() {
        this.showInfo('Tool Browser', 'Detailed tool browser coming soon!');
    }

    showAgentChat() {
        this.showInfo('AI Assistant', 'AI-powered workflow assistance coming soon!');
    }

    viewWorkflow(workflowId) {
        this.showInfo('Workflow Details', `Workflow ${workflowId} details coming soon!`);
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
                <div class="modal-body">
                    ${content}
                </div>
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
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h4>Execution Result:</h4>
                <pre style="background: #1f2937; color: #fbbf24; padding: 15px; border-radius: 6px; overflow-x: auto; white-space: pre-wrap;">
${JSON.stringify(result, null, 2)}
                </pre>
            </div>
        `);
    }

    showInfo(title, message) {
        const modal = this.createModal(title, `
            <div style="padding: 20px; text-align: center;">
                <p style="font-size: 1.1rem; color: #374151;">${message}</p>
            </div>
        `);
    }

    showError(message) {
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }

    showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }
}

// Initialize the application
const app = new IntegrationPlatformUI();
