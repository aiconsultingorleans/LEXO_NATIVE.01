'use client';

import { useState, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/contexts/ToastContext';
import { chatService } from '@/services/chatService';
import { 
  Send, 
  Bot, 
  User, 
  Upload, 
  FileText, 
  X, 
  Loader2,
  MessageSquare,
  Paperclip,
  Download,
  Eye,
  Scan,
  FileUp,
  Zap,
  BarChart3
} from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  attachedDocument?: {
    id: string;
    filename: string;
    analysis?: any;
  };
  isTyping?: boolean;
}

interface AttachedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'ready' | 'error';
  analysis?: any;
}

export default function ChatPage() {
  return (
    <AuthGuard requireAuth={true}>
      <ChatContent />
    </AuthGuard>
  );
}

function ChatContent() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Bonjour ! Je suis Mistral, votre assistant IA pour l\'analyse de documents. Vous pouvez me poser des questions ou soumettre des documents pour analyse. Comment puis-je vous aider aujourd\'hui ?',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<'checking' | 'available' | 'unavailable'>('checking');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  // Check service availability on mount
  useEffect(() => {
    const checkService = async () => {
      const isAvailable = await chatService.isServiceAvailable();
      setServiceStatus(isAvailable ? 'available' : 'unavailable');
      
      if (!isAvailable) {
        toast.warning('Service Mistral', 'Le service Mistral MLX n\'est pas disponible. Démarrez-le avec ./start_document_analyzer.sh');
      }
    };
    
    checkService();
  }, [toast]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const onDrop = async (acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'uploading' as const
    }));

    setAttachedFiles(prev => [...prev, ...newFiles]);
    toast.info('Fichiers ajoutés', `${acceptedFiles.length} fichier(s) en cours d'analyse`);

    // Process files
    for (const attachedFile of newFiles) {
      try {
        // Upload and analyze file
        const formData = new FormData();
        formData.append('file', attachedFile.file);

        const uploadResponse = await fetch('http://localhost:8000/api/v1/documents/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: formData
        });

        if (!uploadResponse.ok) {
          throw new Error('Upload failed');
        }

        const uploadResult = await uploadResponse.json();

        // Get OCR analysis
        const ocrFormData = new FormData();
        ocrFormData.append('file', attachedFile.file);

        const ocrResponse = await fetch('http://localhost:8000/api/v1/ocr/process', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          },
          body: ocrFormData
        });

        let analysis = null;
        if (ocrResponse.ok) {
          analysis = await ocrResponse.json();
          
          // Get Mistral analysis if OCR succeeded
          if (analysis.text) {
            try {
              const mistralResponse = await fetch('http://localhost:8000/api/v1/intelligence/analyze', {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                  text: analysis.text,
                  analysis_types: ['classification', 'key_extraction', 'summary']
                })
              });

              if (mistralResponse.ok) {
                const mistralData = await mistralResponse.json();
                analysis.mistral_analysis = mistralData.result;
              }
            } catch (error) {
              console.error('Mistral analysis failed:', error);
            }
          }
        }

        setAttachedFiles(prev => prev.map(f => 
          f.id === attachedFile.id ? { ...f, status: 'ready', analysis } : f
        ));

        toast.success('Analyse terminée', `"${attachedFile.file.name}" est prêt pour l'analyse`);

      } catch (error) {
        setAttachedFiles(prev => prev.map(f => 
          f.id === attachedFile.id ? { ...f, status: 'error' } : f
        ));
        toast.error('Erreur', `Échec de l'analyse de "${attachedFile.file.name}"`);
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    },
    multiple: true,
    noClick: true
  });

  const removeAttachedFile = (id: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== id));
  };

  const clearConversation = async () => {
    const success = await chatService.clearConversation('lexo-chat');
    if (success) {
      setMessages([
        {
          id: '1',
          type: 'assistant',
          content: 'Conversation effacée. Comment puis-je vous aider ?',
          timestamp: new Date()
        }
      ]);
      toast.success('Conversation effacée', 'Nouvelle conversation démarrée');
    }
  };

  const sendQuickMessage = (message: string) => {
    setInputMessage(message);
    setTimeout(() => sendMessage(), 100);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() && attachedFiles.length === 0) return;
    if (serviceStatus !== 'available') {
      toast.error('Service indisponible', 'Le service Mistral MLX n\'est pas accessible');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage || 'Document soumis pour analyse',
      timestamp: new Date(),
      attachedDocument: attachedFiles.length > 0 ? {
        id: attachedFiles[0].id,
        filename: attachedFiles[0].file.name,
        analysis: attachedFiles[0].analysis
      } : undefined
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    // Add typing indicator
    const typingMessage: Message = {
      id: 'typing',
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isTyping: true
    };
    setMessages(prev => [...prev, typingMessage]);

    try {
      // Use chat service for better handling
      const response = await chatService.sendMessage({
        message: inputMessage,
        conversationId: 'lexo-chat',
        maxTokens: 2000,
        attachedDocument: attachedFiles.length > 0 ? {
          id: attachedFiles[0].id,
          filename: attachedFiles[0].file.name,
          analysis: attachedFiles[0].analysis
        } : undefined
      });

      // Remove typing indicator and add response
      setMessages(prev => prev.filter(m => m.id !== 'typing'));
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);

    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => prev.filter(m => m.id !== 'typing'));
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'Désolé, le service de chat n\'est pas disponible actuellement. Veuillez vérifier que le service Mistral MLX est démarré.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
      toast.error('Service indisponible', 'Le service Mistral MLX n\'est pas accessible');
    } finally {
      setIsLoading(false);
      setAttachedFiles([]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <MainLayout>
      <div className="h-[calc(100vh-6rem)] flex flex-col">
        
        {/* ===== HEADER ===== */}
        <div className="flex-shrink-0 mb-4">
          <Card className="bg-background-secondary/50 border-card-border">
            <div className="p-3">
              <div className="flex items-center justify-between flex-wrap sm:flex-nowrap gap-2">
                <h1 className="text-base sm:text-lg font-bold text-foreground flex items-center gap-2">
                  <div className="p-1.5 bg-primary/10 rounded-lg">
                    <MessageSquare className="h-4 w-4 text-primary" />
                  </div>
                  <span className="hidden sm:inline">Chat Intelligence Documentaire</span>
                  <span className="sm:hidden">Chat IA</span>
                  <div className={`w-2 h-2 rounded-full ${
                    serviceStatus === 'available' ? 'bg-success' :
                    serviceStatus === 'unavailable' ? 'bg-error' : 'bg-warning'
                  }`} title={
                    serviceStatus === 'available' ? 'Service disponible' :
                    serviceStatus === 'unavailable' ? 'Service indisponible' : 'Vérification...'
                  } />
                </h1>
                <div className="flex items-center gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-1 h-8 px-2 sm:px-3"
                  >
                    <FileUp className="h-3 w-3" />
                    <span className="hidden sm:inline">Upload</span>
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={clearConversation}
                    className="flex items-center gap-1 h-8 px-2 sm:px-3"
                  >
                    <X className="h-3 w-3" />
                    <span className="hidden sm:inline">Effacer</span>
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* ===== ZONE DE CONVERSATION ===== */}
        <div className="flex-1 min-h-0 mb-4">
          <Card className="h-full bg-background-secondary/30 border-card-border overflow-hidden">
            <div className="h-full flex flex-col">
              <div 
                className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3"
                {...getRootProps()}
              >
                <input {...getInputProps()} />
              
                {isDragActive && (
                  <div className="fixed inset-0 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center z-50">
                    <div className="text-center">
                      <Upload className="h-12 w-12 text-primary mx-auto mb-4" />
                      <p className="text-lg font-medium text-primary">Déposez vos documents ici</p>
                      <p className="text-sm text-foreground-secondary">PDF, PNG, JPG, JPEG, TIFF, BMP</p>
                    </div>
                  </div>
                )}

                {messages.map((message) => (
                  <div key={message.id} className="w-full">
                    {message.type === 'user' ? (
                      /* Message utilisateur */
                      <div className="flex justify-end mb-2">
                        <div className="flex items-start gap-2 max-w-[85%] sm:max-w-[70%]">
                          <div className="bg-primary text-white rounded-2xl rounded-tr-md px-3 py-2 shadow-sm">
                            <p className="text-sm leading-relaxed break-words">{message.content}</p>
                            {message.attachedDocument && (
                              <div className="mt-2 p-2 bg-white/10 rounded">
                                <div className="flex items-center gap-2">
                                  <FileText className="h-3 w-3" />
                                  <span className="text-xs font-medium truncate">{message.attachedDocument.filename}</span>
                                </div>
                              </div>
                            )}
                          </div>
                          <div className="flex-shrink-0 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                            <User className="h-3 w-3 text-white" />
                          </div>
                        </div>
                      </div>
                    ) : (
                      /* Message assistant */
                      <div className="flex justify-start mb-2">
                        <div className="flex items-start gap-2 max-w-[85%] sm:max-w-[70%]">
                          <div className="flex-shrink-0 w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                            <Bot className="h-3 w-3 text-primary" />
                          </div>
                          <div className="bg-background border border-card-border/30 rounded-2xl rounded-tl-md px-3 py-2 shadow-sm">
                            {message.isTyping ? (
                              <div className="flex items-center gap-2">
                                <Loader2 className="h-3 w-3 animate-spin text-primary" />
                                <span className="text-xs text-foreground-secondary">Mistral analyse...</span>
                              </div>
                            ) : (
                              <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap break-words">
                                {message.content}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Timestamp */}
                    <div className={`text-xs text-foreground-muted mb-2 ${
                      message.type === 'user' ? 'text-right pr-8' : 'pl-8'
                    }`}>
                      {message.timestamp.toLocaleTimeString('fr-FR', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            </div>
          </Card>
        </div>

        {/* ===== ZONE DE SAISIE ===== */}
        <div className="flex-shrink-0">
          <Card className="bg-background-secondary/50 border-card-border">
            <div className="p-3">
              {/* Documents attachés - Très compact */}
              {attachedFiles.length > 0 && (
                <div className="mb-3 p-2 bg-background-secondary/30 rounded border border-card-border/50">
                  <div className="flex items-center gap-2">
                    <FileText className="h-3 w-3" />
                    <span className="text-xs font-medium text-foreground">
                      {attachedFiles.length} document(s)
                    </span>
                    <div className="flex gap-1 ml-auto">
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => sendQuickMessage("Résume ces documents")}
                        disabled={attachedFiles.every(f => f.status !== 'ready')}
                        className="h-5 px-2 text-xs"
                      >
                        Résumer
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => setAttachedFiles([])}
                        className="h-5 w-5 p-0 text-foreground-muted hover:text-error"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {attachedFiles.map((file) => (
                      <div key={file.id} className="flex items-center gap-1 bg-background rounded px-2 py-0.5 border border-card-border text-xs">
                        <span className="font-medium truncate max-w-[80px]">{file.file.name}</span>
                        {file.status === 'uploading' && <Loader2 className="h-2 w-2 animate-spin text-primary" />}
                        {file.status === 'ready' && <div className="w-1 h-1 bg-success rounded-full" />}
                        {file.status === 'error' && <div className="w-1 h-1 bg-error rounded-full" />}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Zone de saisie principale */}
              <div className="flex flex-col sm:flex-row gap-2 sm:items-end">
                <div className="flex-1">
                  <div className="flex gap-2 items-center">
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="flex-shrink-0 p-2 text-foreground-muted hover:text-primary hover:bg-primary/5 rounded transition-all"
                      title="Joindre un document"
                    >
                      <Paperclip className="h-4 w-4" />
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files) {
                          onDrop(Array.from(e.target.files));
                        }
                      }}
                    />
                    
                    <div className="flex-1">
                      <textarea
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Posez votre question ou uploadez un document..."
                        className="w-full resize-none rounded border border-card-border bg-background px-3 py-2 text-sm text-foreground placeholder-foreground-muted focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary transition-all min-h-[2.5rem]"
                        rows={1}
                      />
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 justify-between sm:justify-end">
                  <div className="flex items-center gap-1">
                    {serviceStatus === 'available' && (
                      <span className="text-xs text-success flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-success rounded-full" />
                        <span className="hidden sm:inline">Actif</span>
                      </span>
                    )}
                    {serviceStatus !== 'available' && (
                      <span className="text-xs text-error flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-error rounded-full" />
                        <span className="hidden sm:inline">OFF</span>
                      </span>
                    )}
                  </div>
                  
                  <Button
                    onClick={sendMessage}
                    disabled={(!inputMessage.trim() && attachedFiles.length === 0) || isLoading || serviceStatus !== 'available'}
                    className="flex-shrink-0 px-3 py-2 rounded min-w-[4rem]"
                    size="sm"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-4 w-4 mr-1" />
                        <span className="hidden sm:inline">Envoyer</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}