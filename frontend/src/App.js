import { useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
    // Estado de UI
    const [isBatchMode, setIsBatchMode] = useState(false);
    
    // Estado Calculadora Simple
    const [a, setA] = useState("");
    const [b, setB] = useState("");
    
    // Estado Batch
    const [batchInput, setBatchInput] = useState('[{"op": "sum", "nums": [10, 20]}, {"op": "multiply", "nums": [2, 3, 4]}]');
    
    // Resultados y Errores
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    
    // Historial
    const [history, setHistory] = useState([]);
    const [filterOp, setFilterOp] = useState("");
    const [sortOrder, setSortOrder] = useState("desc");

    const API_URL = "http://localhost:8089/calculadora-fast-api";

    // --- Funciones Auxiliares ---

    const handleFetch = async (url, options = {}) => {
        setError(null);
        setResult(null);
        try {
            const res = await fetch(url, options);
            const data = await res.json();
            
            if (!res.ok) {
                // Manejo de errores estructurados del backend
                const errorMsg = data.detail?.error || data.detail || "Error";
                setError(errorMsg);
                return null;
            }
            return data;
        } catch (e) {
            setError("Error de conexión con el servidor.");
            return null;
        }
    };

    const refreshHistory = useCallback(async () => {
        let url = `${API_URL}/history?sort_order=${sortOrder}`;
        if (filterOp) url += `&operation=${filterOp}`;
        
        const data = await handleFetch(url);
        if (data) setHistory(data.history);
    }, [filterOp, sortOrder]);

    // --- Operaciones ---

    const executeSingleOp = async (operation) => {
        if (a === "" || b === "") {
            setError("Por favor ingresa ambos números.");
            return;
        }
        // Usamos los endpoints GET individuales que ya tienes
        const data = await handleFetch(`${API_URL}/${operation}?a=${a}&b=${b}`);
        
        if (data) {
            setResult(data.result);
            refreshHistory();
        }
    };

    const executeBatch = async () => {
        try {
            const payload = JSON.parse(batchInput);
            const data = await handleFetch(`${API_URL}/batch_operations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (data) {
                // Formatear resultado batch para visualización
                setResult(JSON.stringify(data, null, 2));
                refreshHistory();
            }
        } catch (e) {
            setError("JSON inválido. Revisa el formato.");
        }
    };

    // --- Efectos ---

    useEffect(() => {
        refreshHistory();
    }, [refreshHistory]);

    // --- Render ---

    return (
        <div className="app-container">
            <header className="app-header">
                <h1>CALCULADORA FASTAPI</h1>
            </header>

            <main className="main-grid">
                {/* SECCIÓN IZQUIERDA: CALCULADORA */}
                <section className="card calculator-section">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h2>{isBatchMode ? "Modo Batch" : "Modo Simple"}</h2>
                        <button 
                            className="mode-toggle" 
                            onClick={() => { setIsBatchMode(!isBatchMode); setError(null); setResult(null); }}
                            style={{ width: 'auto', marginTop: 0, padding: '5px 10px', fontSize: '0.8rem' }}
                        >
                            Cambiar Modo ⇄
                        </button>
                    </div>

                    {isBatchMode ? (
                        // UI MODO BATCH
                        <>
                            <textarea 
                                className="json-input"
                                value={batchInput}
                                onChange={(e) => setBatchInput(e.target.value)}
                                placeholder='[{"op": "sum", "nums": [1, 2]}]'
                            />
                            <button className="btn-batch" onClick={executeBatch}>Ejecutar Batch</button>
                            <p style={{fontSize: '0.8rem', color: '#666'}}>* Soporta N números por operación</p>
                        </>
                    ) : (
                        // UI MODO SIMPLE
                        <>
                            <div className="input-group">
                                <input 
                                    type="number" 
                                    placeholder="Número A" 
                                    value={a} 
                                    onChange={(e) => setA(e.target.value)} 
                                />
                            </div>
                            <div className="input-group">
                                <input 
                                    type="number" 
                                    placeholder="Número B" 
                                    value={b} 
                                    onChange={(e) => setB(e.target.value)} 
                                />
                            </div>

                            <div className="btn-group">
                                <button className="btn-action" onClick={() => executeSingleOp('sum')}>Sumar (+)</button>
                                <button className="btn-action" onClick={() => executeSingleOp('subtract')}>Restar (-)</button>
                                <button className="btn-action" onClick={() => executeSingleOp('multiply')}>Multiplicar (×)</button>
                                <button className="btn-action" onClick={() => executeSingleOp('divide')}>Dividir (÷)</button>
                            </div>
                        </>
                    )}

                    {/* DISPLAY RESULTADOS / ERRORES */}
                    {(result !== null || error) && (
                        <div className="result-box" style={{ border: error ? '1px solid #f44336' : '1px solid #4caf50' }}>
                            {error ? (
                                <p className="error-text">⚠️ {error}</p>
                            ) : (
                                isBatchMode ? (
                                    <pre style={{textAlign: 'left', color: '#4caf50', overflowX: 'auto'}}>{result}</pre>
                                ) : (
                                    <p className="result-text">Resultado: {result}</p>
                                )
                            )}
                        </div>
                    )}
                </section>

                {/* SECCIÓN DERECHA: HISTORIAL */}
                <section className="card history-section">
                    <h2>Historial de Operaciones</h2>
                    
                    <div className="filters">
                        <select value={filterOp} onChange={(e) => setFilterOp(e.target.value)}>
                            <option value="">Todas las operaciones</option>
                            <option value="sum">Suma</option>
                            <option value="subtract">Resta</option>
                            <option value="multiply">Multiplicación</option>
                            <option value="divide">División</option>
                        </select>
                        
                        <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
                            <option value="desc">Más recientes</option>
                            <option value="asc">Más antiguos</option>
                        </select>
                    </div>

                    <ul className="history-list">
                        {history.length === 0 ? (
                            <p style={{color: '#666', textAlign: 'center'}}>No hay registros.</p>
                        ) : (
                            history.map((item, i) => (
                                <li key={i} className="history-item">
                                    <div>
                                        <span className="history-op">{item.operation.toUpperCase()}</span>
                                        <span style={{ fontWeight: 'bold' }}>
                                            {item.a} {getSymbol(item.operation)} {item.b} = <span style={{color: 'var(--accent-color)'}}>{item.result}</span>
                                        </span>
                                    </div>
                                    <span className="history-date">
                                        {new Date(item.date).toLocaleTimeString()}
                                    </span>
                                </li>
                            ))
                        )}
                    </ul>
                </section>
            </main>
        </div>
    );
}

const getSymbol = (op) => {
    switch(op) {
        case 'sum': return '+';
        case 'subtract': return '-';
        case 'multiply': return '×';
        case 'divide': return '÷';
        default: return '?';
    }
};

export default App;
