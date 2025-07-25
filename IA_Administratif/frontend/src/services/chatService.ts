interface ChatRequest {
  message: string;
  conversationId?: string;
  maxTokens?: number;
  attachedDocument?: {
    id: string;
    filename: string;
    analysis?: any;
  };
}

interface ChatResponse {
  response: string;
  conversationId: string;
  timestamp: string;
  tokens_used?: number;
}

class ChatService {
  private baseUrl = 'http://localhost:8004';

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      // Prepare enhanced context for Mistral
      let enhancedMessage = request.message;
      
      if (request.attachedDocument?.analysis) {
        const analysis = request.attachedDocument.analysis;
        enhancedMessage += `\n\n=== DOCUMENT ANALYSÉ ===`;
        enhancedMessage += `\nFichier: ${request.attachedDocument.filename}`;
        
        if (analysis.text) {
          enhancedMessage += `\nContenu OCR: ${analysis.text}`;
        }
        
        if (analysis.mistral_analysis) {
          const mistralAnalysis = analysis.mistral_analysis;
          if (mistralAnalysis.classification) {
            enhancedMessage += `\nType de document: ${mistralAnalysis.classification.type}`;
            enhancedMessage += `\nConfiance classification: ${mistralAnalysis.classification.confidence}`;
          }
          
          if (mistralAnalysis.entities) {
            enhancedMessage += `\nEntités détectées:`;
            if (mistralAnalysis.entities.dates?.length > 0) {
              enhancedMessage += `\n- Dates: ${mistralAnalysis.entities.dates.join(', ')}`;
            }
            if (mistralAnalysis.entities.amounts?.length > 0) {
              enhancedMessage += `\n- Montants: ${mistralAnalysis.entities.amounts.join(', ')}`;
            }
            if (mistralAnalysis.entities.companies?.length > 0) {
              enhancedMessage += `\n- Entreprises: ${mistralAnalysis.entities.companies.join(', ')}`;
            }
          }
          
          if (mistralAnalysis.summary) {
            enhancedMessage += `\nRésumé: ${mistralAnalysis.summary}`;
          }
        }
        
        enhancedMessage += `\n=== FIN DOCUMENT ===\n`;
      }

      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: enhancedMessage,
          conversation_id: request.conversationId || 'lexo-chat',
          max_tokens: request.maxTokens || 2000,
          system_prompt: this.getSystemPrompt()
        })
      });

      if (!response.ok) {
        throw new Error(`Chat service error: ${response.status}`);
      }

      const data = await response.json();
      
      return {
        response: data.response || 'Désolé, je n\'ai pas pu traiter votre demande.',
        conversationId: data.conversation_id || request.conversationId || 'lexo-chat',
        timestamp: new Date().toISOString(),
        tokens_used: data.tokens_used
      };

    } catch (error) {
      console.error('Chat service error:', error);
      throw new Error('Service de chat indisponible. Vérifiez que Mistral MLX est démarré.');
    }
  }

  private getSystemPrompt(): string {
    return `Tu es Mistral, un assistant IA spécialisé dans l'analyse de documents administratifs pour LEXO v1.

CONTEXTE:
- Tu aides les utilisateurs à analyser leurs documents (factures, RIB, impôts, attestations, contrats)
- Tu peux expliquer le contenu des documents, extraire des informations clés, et répondre aux questions
- Les documents ont déjà été traités par OCR et analyse préliminaire

CAPACITÉS:
- Analyse et résumé de documents
- Extraction d'informations clés (dates, montants, entités)
- Classification et catégorisation
- Réponse aux questions sur le contenu
- Conseils sur l'organisation documentaire

STYLE:
- Sois professionnel mais accessible
- Utilise un langage clair et précis
- Structure tes réponses avec des puces ou sections si nécessaire
- Cite les éléments spécifiques du document quand pertinent
- Si tu n'es pas sûr, indique-le clairement

SÉCURITÉ:
- Ne jamais révéler d'informations personnelles sensibles
- Respecter la confidentialité
- Signaler si un document semble contenir des données sensibles`;
  }

  async getConversationHistory(conversationId: string): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (response.ok) {
        const data = await response.json();
        return data.messages || [];
      }
    } catch (error) {
      console.error('Failed to get conversation history:', error);
    }
    
    return [];
  }

  async clearConversation(conversationId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      return response.ok;
    } catch (error) {
      console.error('Failed to clear conversation:', error);
      return false;
    }
  }

  isServiceAvailable(): Promise<boolean> {
    return fetch(`${this.baseUrl}/health`)
      .then(response => response.ok)
      .catch(() => false);
  }
}

export const chatService = new ChatService();
export type { ChatRequest, ChatResponse };