import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-card p-6 border-l-4 border-red-400 bg-red-50 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="font-medium text-red-800">Panel rendering error</p>
              <p className="text-xs text-red-600 mt-0.5">
                {this.state.error?.message || 'Unknown error'}
              </p>
            </div>
          </div>
          <p className="text-xs text-red-500 font-mono bg-red-100 p-2 rounded-lg">
            {this.state.error?.stack?.split('\n').slice(0, 3).join('\n')}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="btn-secondary text-xs py-1.5 px-3"
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
