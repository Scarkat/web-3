import { useState, useEffect, useCallback } from 'react';
import './App.css';

function App() {
    const [isBatchMode, setIsBatchMode] = useState(false); 

    const [operands, setOperands] = useState(["", ""]); // Inicializamos con dos inputs
    const [resultado, setResultado] = useState(null);
    const [error, setError] = useState(null);

    const [operationQueue, setOperationQueue] = useState([]);
    const [queueResult, setQueueResult] = useState(null); 
    const [queueError, setQueueError] = useState(null);
    
    const [historial, setHistorial] = useState([]);
    const [filterOp, setFilterOp] = useState('');
    const [orderBy, setOrderBy] = useState('date');
    const [sortOrder, setSortOrder] = useState('desc');
    
    
    const handleOperandChange = (e, index) => {
        const newOperands = [...operands];
        newOperands[index] = e.target.value;
        setOperands(newOperands); 
        setError(null);
    };

    const addOperand = () => {
        setOperands(prev => [...prev, ""]);
    };

    const removeOperand = (indexToRemove) => {
        setOperands(prev => prev.filter((_, index) => index !== indexToRemove));
        setError(null);
    };

    const isInputValid = () => {
        if (operands.length < 2) {
            return false;
        }

        // Iterar sobre todos los operandos
        for (const operand of operands) {
            const num = parseFloat(operand);
            
            // 1. Campo vacío (no se considera válido si hay alguno vacío)
            if (operand.trim() === "") {
                return false;
            }
            // 2. Si no es un número válido (NaN)
            if (isNaN(num)) {
                return false;
            }
            // 3. Deshabilita si es un valor negativo
            if (num < 0) {
                 return false;
            }
        }
        return true;
    };

    // --- Lógica de Historial (Memorizada) ---
    const obtenerHistorial = useCallback(async () => {
        try {
            const queryParams = new URLSearchParams();
            if (filterOp) queryParams.append('operation', filterOp);
            queryParams.append('order_by', orderBy);
            queryParams.append('sort_order', sortOrder);

            const url = `http://localhost:8089/calculadora-fast-api/history?${queryParams.toString()}`;
            
            const res = await fetch(url);
            if (!res.ok) {
                throw new Error("Fallo al cargar el historial");
            }
            const data = await res.json();
            setHistorial(data.history); 
        } catch (e) {
            console.error("No se pudo obtener el historial", e);
        }
    }, [filterOp, orderBy, sortOrder]); 

    useEffect(() => {
        obtenerHistorial(); 
    }, [obtenerHistorial]);

    useEffect(() => {
        if (resultado !== null || queueResult !== null) {
            obtenerHistorial();
        }
    }, [resultado, queueResult]);

    // --- Lógica de Ejecución de Operación Individual ---
    const ejecutarOperacion = async (endpoint) => {
        setError(null); 
        setResultado(null);
        
        const numericOperands = operands.map(parseFloat);

        // VALIDACIÓN DE NEGATIVOS Y NÚMERO DE OPERANDOS AL HACER CLIC
        if (numericOperands.some(isNaN) || numericOperands.some(n => n < 0)) {
            setError("Los números no pueden ser negativos y deben ser válidos.");
            return;
        }
        if (operands.length < 2) {
            setError("La operación requiere al menos 2 números.");
            return;
        }
        if (!isInputValid()) {
            setError("Asegúrate de que todos los campos no estén vacíos.");
            return;
        }

        try {
            const payload = [{ op: endpoint, nums: numericOperands }];

            const res = await fetch(`http://localhost:8089/calculadora-fast-api/batch_operations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await res.json();
            
            if (!res.ok || data[0].error) {
                const errorData = data[0].error ? data[0] : { error: data.detail || 'Error desconocido' };
                let errorMessage = errorData.error;
                if (errorData.operation) {
                    errorMessage += ` (Op: ${errorData.operation})`;
                }
                
                setError(errorMessage);
                return;
            }

            setResultado(data[0].result);
            obtenerHistorial(); 
        } catch (e) {
            setError("Error de conexión con el servidor o fallo en la red.");
            console.error(e);
        }
    };

    // Funciones para acumular operaciones en la cola
    const handleQueueOperation = (op) => {
        const numericOperands = operands.map(parseFloat);
        
        // VALIDACIÓN DE NEGATIVOS Y NÚMERO DE OPERANDOS AL AÑADIR A COLA
        if (numericOperands.some(isNaN) || numericOperands.some(n => n < 0)) {
            setError("Los números no pueden ser negativos y deben ser válidos.");
            return;
        }
        if (operands.length < 2) {
            setError("La operación requiere al menos 2 números.");
            return;
        }
        if (!isInputValid()) {
            setError("Asegúrate de que todos los campos no estén vacíos.");
            return;
        }
        
        const newOperation = { 
            op: op, 
            nums: numericOperands
        };
        
        setOperationQueue(prev => [...prev, newOperation]);
        setOperands(["", ""]); // Limpiar inputs
        setError(null); 
    }

    // Funciones de manejo para cada botón (dependen del modo)
    const sumar = isBatchMode ? () => handleQueueOperation('sum') : () => ejecutarOperacion('sum');
    const restar = isBatchMode ? () => handleQueueOperation('subtract') : () => ejecutarOperacion('subtract');
    const multiplicar = isBatchMode ? () => handleQueueOperation('multiply') : () => ejecutarOperacion('multiply');
    const dividir = isBatchMode ? () => ejecutarOperacion('divide') : () => ejecutarOperacion('divide');


    // --- Lógica del Batch ---
    const executeQueue = async () => {
        setQueueResult(null);
        setQueueError(null);
        
        if (operationQueue.length === 0) {
            setQueueError("La cola de operaciones está vacía.");
            return;
        }

        try {
            const res = await fetch(`http://localhost:8089/calculadora-fast-api/batch_operations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(operationQueue),
            });

            const data = await res.json();
            
            if (!res.ok) {
                setQueueError(`Error ${res.status}: ${data.detail || 'Fallo de servidor'}`);
                return;
            }
            
            setQueueResult(data);
            setOperationQueue([]);
            obtenerHistorial();
            
        } catch (e) {
            setQueueError("Error de conexión o fallo en la red.");
            console.error(e);
        }
    };
    
    // --- COMPONENTE DE INPUT DINÁMICO REUTILIZABLE ---
    const DynamicInputSection = ({ isBatch }) => (
        <>
            {operands.map((operand, index) => (
                <div key={index} className="operand-input-group">
                    <input
                        type="text"
                        value={operand}
                        onChange={(e) => handleOperandChange(e, index)} 
                        placeholder={`Número ${index + 1}`}
                    />

                    {/* Botón de resta solo si hay más de 2 inputs */}
                    {operands.length > 2 && (
                        <button 
                            className="remove-operand-btn" 
                            onClick={() => removeOperand(index)}
                            style={{backgroundColor: '#f44336', flexShrink: 0, padding: '0 8px'}}
                        >
                            -
                        </button>
                    )}
                </div>
            ))}
            
            {/* Botón de suma para añadir nuevo input */}
            <button className="add-operand-btn" onClick={addOperand} style={{backgroundColor: '#4caf50'}}>
                + Añadir Número
            </button>
            
            <div className="button-group">
                <button onClick={sumar} disabled={!isInputValid()}>{isBatch ? 'Añadir SUMA' : 'SUMAR (+)'}</button>
                <button onClick={restar} disabled={!isInputValid()}>{isBatch ? 'Añadir RESTA' : 'RESTAR (-)'}</button>
                <button onClick={multiplicar} disabled={!isInputValid()}>{isBatch ? 'Añadir MULT' : 'MULTIPLICAR (x)'}</button>
                <button onClick={dividir} disabled={!isInputValid()}>{isBatch ? 'Añadir DIV' : 'DIVIDIR (/)'}</button>
            </div>
        </>
    );


    // --- Componente de Calculadora de Cola (Columna Izquierda) ---
    const QueueCalculator = () => (
        <div className="calculator-section batch-mode">
            <h2 className="title-section">Calculadora por Lista (N-Números)</h2>
            <p className="batch-info">Añade operaciones a la lista y ejecuta.</p>

            <DynamicInputSection isBatch={true} />
            
            <div className="queue-display">
                <h4>Lista ({operationQueue.length} ops):</h4>
                <div className="queue-list">
                    {operationQueue.length > 0 ? (
                        operationQueue.map((op, index) => (
                            <span key={index} className="queue-item">{op.op.substring(0, 3).toUpperCase()} ({op.nums.join(', ')})</span>
                        ))
                    ) : (
                        <p className="no-history">Lista vacía. Añade una operación.</p>
                    )}
                </div>
            </div>

            <button onClick={executeQueue} disabled={operationQueue.length === 0} className="batch-execute-btn">
                EJECUTAR LISTA ({operationQueue.length})
            </button>

            <div className="result-area">
                {error && <p className="error-message">❌ Error: {error}</p>} 
                {queueError && <p className="error-message">❌ Error de lista: {queueError}</p>} 
                {queueResult && (
                    <>
                        <p className="result-message">✅ Resultados:</p>
                        <pre className="batch-output">{JSON.stringify(queueResult, null, 2)}</pre>
                    </>
                )}
            </div>
            
            <button className="toggle-mode-btn" onClick={() => setIsBatchMode(false)}>
                MODO NORMAL
            </button>
        </div>
    );
    

    // --- Componente de Operación Individual (Columna Izquierda) ---
    const IndividualCalculator = () => (
        <div className="calculator-section">
            <h2 className="title-section">Calculadora Simple (N-Números)</h2>
            
            <DynamicInputSection isBatch={false} />

            <div className="result-area">
                {error && <p className="error-message">❌ Error: {error}</p>} 
                {resultado !== null && <p className="result-message">Resultado: {resultado}</p>}
            </div>
            
            <button className="toggle-mode-btn" onClick={() => {
                setOperands(["", ""]); setResultado(null); setError(null);
                setIsBatchMode(true);
            }}>
                MODO LISTA
            </button>
        </div>
    );
    

    // --- Renderizado Principal (Estructura de Columnas) ---
    return (
        <div className="app-container">
            <header className="app-header">
                <h1>CALCULADORA by ANDY</h1>
            </header>

            <main className="main-content-grid">
                {/* Columna Izquierda: Calculadora (Simple o Cola) */}
                <div className="left-column">
                    {isBatchMode ? <QueueCalculator /> : <IndividualCalculator />}
                </div>

                {/* Columna Derecha: Historial y Filtros */}
                <div className="right-column history-section">
                    <h2 className="title-section">Historial (Últimos 10)</h2>

                    <div className="filter-group">
                        <select value={filterOp} onChange={(e) => setFilterOp(e.target.value)}>
                            <option value="">Todas las Ops</option>
                            <option value="sum">Suma</option>
                            <option value="subtract">Resta</option>
                            <option value="multiply">Multiplicación</option>
                            <option value="divide">División</option>
                        </select>
                        
                        <select value={orderBy} onChange={(e) => setOrderBy(e.target.value)}>
                            <option value="date">Ordenar por Fecha</option>
                            <option value="result">Ordenar por Resultado</option>
                        </select>
                        
                        <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
                            <option value="desc">Descendente</option>
                            <option value="asc">Ascendente</option>
                        </select>
                    </div>

                    <ul className="history-list">
                        {historial.map((op, i) => {
                            const symbol = 
                                op.operation === 'sum' ? '+' : 
                                op.operation === 'subtract' ? '-' : 
                                op.operation === 'multiply' ? 'x' : 
                                op.operation === 'divide' ? '/' : '?';

                            return (
                                <li key={i} className="history-item">
                                    <span className={`op-tag op-${op.operation}`}>{op.operation.toUpperCase()}</span>
                                    {op.a} {symbol} {op.b} ... = <strong>{op.result}</strong>
                                    <span className="date-time">({new Date(op.date).toLocaleTimeString()})</span>
                                </li>
                            );
                        })}
                    </ul>
                    {historial.length === 0 && <p className="no-history">El historial está vacío o no coincide con los filtros.</p>}
                </div>
            </main>
        </div>
    );
}

export default App;