import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        console.error('Error caught by boundary:', error, errorInfo);
        this.setState({
            error,
            errorInfo
        });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-4">
                    <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl w-full">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="bg-red-100 p-3 rounded-full">
                                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-bold text-gray-800">Oops! Something went wrong</h2>
                        </div>
                        
                        <p className="text-gray-600 mb-4">
                            We're sorry, but something unexpected happened. Please try refreshing the page.
                        </p>
                        
                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <details className="mt-4 p-4 bg-gray-100 rounded-lg">
                                <summary className="cursor-pointer font-semibold text-gray-700 mb-2">
                                    Error Details (Development Only)
                                </summary>
                                <div className="mt-2 text-sm">
                                    <p className="text-red-600 font-mono mb-2">{this.state.error.toString()}</p>
                                    <pre className="text-xs overflow-auto bg-white p-2 rounded border">
                                        {this.state.errorInfo?.componentStack}
                                    </pre>
                                </div>
                            </details>
                        )}
                        
                        <button
                            onClick={() => window.location.reload()}
                            className="mt-6 bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
                        >
                            Refresh Page
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
