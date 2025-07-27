import logging
import re
import random
from typing import List, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
from models.debate import DebateArgument
from models.personality import AIPersonality
from services.personality_service import PersonalityService
from config import Config

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.personality_service = PersonalityService()
        self.model_name = Config.DEFAULT_MODEL
        self.tokenizer = None
        self.model = None
        self.generator = None
        self.fallback_generator = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize AI models with fallback options"""
        try:
            logger.info(f"Initializing AI model: {self.model_name}")
            
            # Try to initialize the primary model
            self._load_primary_model()
            
        except Exception as e:
            logger.error(f"Failed to initialize primary model: {str(e)}")
            self._load_fallback_model()
    
    def _load_primary_model(self):
        """Load the primary AI model"""
        try:
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Initialize text generation pipeline
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.8,
                max_length=512
            )
            
            logger.info("Primary AI model initialized successfully")
            
        except Exception as e:
            logger.error(f"Primary model initialization failed: {str(e)}")
            raise
    
    def _load_fallback_model(self):
        """Load fallback model if primary fails"""
        try:
            logger.info(f"Loading fallback model: {Config.BACKUP_MODEL}")
            self.generator = pipeline(
                "text-generation", 
                model=Config.BACKUP_MODEL,
                do_sample=True,
                temperature=0.7,
                max_length=256
            )
            logger.info("Fallback model loaded successfully")
            
        except Exception as e:
            logger.error(f"Fallback model also failed: {str(e)}")
            # Final fallback - use simple model
            try:
                self.generator = pipeline("text-generation", model=Config.FALLBACK_MODEL)
                logger.info("Final fallback model loaded")
            except Exception as final_error:
                logger.error(f"All models failed: {str(final_error)}")
                self.generator = None
    
    def generate_debate_round(self, debate, round_number: int) -> List[DebateArgument]:
        """Generate arguments for all personalities for a given round"""
        arguments = []
        personalities = self.personality_service.get_debate_personalities()
        
        # Shuffle personalities for varied order
        personalities = list(personalities)
        random.shuffle(personalities)
        
        # Get previous arguments for context
        previous_context = self._build_context(debate, round_number)
        
        for personality in personalities:
            try:
                argument_text = self._generate_argument(
                    personality, 
                    debate.topic, 
                    previous_context,
                    round_number,
                    arguments  # Pass already generated arguments for this round
                )
                
                argument = DebateArgument(
                    personality_id=personality.name,
                    content=argument_text,
                    round_number=round_number
                )
                
                arguments.append(argument)
                logger.info(f"Generated argument for {personality.name}: {argument_text[:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to generate argument for {personality.name}: {str(e)}")
                # Create a fallback argument
                fallback_argument = self._create_fallback_argument(personality, debate.topic, round_number)
                arguments.append(fallback_argument)
        
        return arguments
    
    def _generate_argument(self, personality: AIPersonality, topic: str, 
                          context: str, round_number: int, current_round_args: List[DebateArgument] = None) -> str:
        """Generate a single argument for a personality"""
        
        # Build the prompt with current round context
        prompt = self._build_enhanced_prompt(personality, topic, context, round_number, current_round_args)
        
        if not self.generator:
            return self._generate_fallback_argument(personality, topic, round_number)
        
        try:
            # Generate text with enhanced parameters
            response = self.generator(
                prompt,
                max_new_tokens=80,  # Limit new tokens to control length
                num_return_sequences=1,
                temperature=0.8,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id if self.tokenizer else None
            )
            
            generated_text = response[0]['generated_text']
            
            # Extract only the new generated part
            argument = generated_text[len(prompt):].strip()
            
            # Clean up the argument
            argument = self._clean_and_validate_argument(argument)
            
            # Ensure it meets requirements
            if len(argument) < 20:  # Too short
                return self._generate_fallback_argument(personality, topic, round_number)
            
            if len(argument) > Config.MAX_ARGUMENT_LENGTH:
                argument = argument[:Config.MAX_ARGUMENT_LENGTH-3] + "..."
            
            return argument
            
        except Exception as e:
            logger.error(f"Error in text generation for {personality.name}: {str(e)}")
            return self._generate_fallback_argument(personality, topic, round_number)
    
    def _build_enhanced_prompt(self, personality: AIPersonality, topic: str, 
                              context: str, round_number: int, current_round_args: List[DebateArgument] = None) -> str:
        """Build an enhanced prompt for argument generation"""
        
        round_context = self._get_round_context(round_number)
        
        # Add current round arguments if available
        current_round_context = ""
        if current_round_args:
            current_round_context = "\n\nOther participants in this round have said:\n"
            for arg in current_round_args[-2:]:  # Last 2 arguments to avoid too much context
                current_round_context += f"- {arg.personality_id}: {arg.content[:100]}...\n"
        
        prompt = f"""{personality.system_prompt}

DEBATE TOPIC: {topic}
{round_context}

{context}
{current_round_context}

As {personality.name}, provide your {round_number} argument. Be specific, compelling, and stay true to your personality. 
Argument:"""
        
        return prompt.strip()
    
    def _get_round_context(self, round_number: int) -> str:
        """Get context description for the current round"""
        if round_number == 1:
            return "ROUND 1: Present your opening argument and establish your position."
        elif round_number == 2:
            return "ROUND 2: Respond to previous arguments and strengthen your position."
        else:
            return f"ROUND {round_number}: Final arguments - make your strongest case."
    
    def _build_context(self, debate, current_round: int) -> str:
        """Build context from previous arguments"""
        if current_round == 1:
            return ""
        
        context_parts = []
        for arg in debate.arguments:
            if arg['round_number'] < current_round:
                context_parts.append(f"Round {arg['round_number']} - {arg['personality_id']}: {arg['content'][:150]}...")
        
        if not context_parts:
            return ""
        
        return "\nPREVIOUS ROUNDS:\n" + "\n".join(context_parts[-8:])  # Last 8 for context
    
    def _clean_and_validate_argument(self, argument: str) -> str:
        """Clean up and validate the generated argument"""
        if not argument:
            return ""
        
        # Remove common unwanted patterns
        argument = re.sub(r'^["\']|["\']$', '', argument)  # Remove surrounding quotes
        argument = re.sub(r'\n+', ' ', argument)  # Replace newlines with spaces
        argument = re.sub(r'\s+', ' ', argument)  # Normalize whitespace
        argument = re.sub(r'^(As|I am|I\'m)\s+\w+[,:]?\s*', '', argument, flags=re.IGNORECASE)  # Remove self-references
        
        # Remove incomplete sentences at the end
        sentences = argument.split('. ')
        if len(sentences) > 1:
            # Check if last sentence is incomplete (no ending punctuation)
            if not sentences[-1].rstrip().endswith(('.', '!', '?')):
                argument = '. '.join(sentences[:-1])
                if argument and not argument.endswith('.'):
                    argument += '.'
        
        # Ensure it ends with proper punctuation
        argument = argument.strip()
        if argument and not argument.endswith(('.', '!', '?')):
            argument += '.'
        
        return argument
    
    def _create_fallback_argument(self, personality: AIPersonality, topic: str, round_number: int) -> DebateArgument:
        """Create a fallback argument when AI generation fails"""
        fallback_text = self._generate_fallback_argument(personality, topic, round_number)
        return DebateArgument(
            personality_id=personality.name,
            content=fallback_text,
            round_number=round_number
        )
    
    def _generate_fallback_argument(self, personality: AIPersonality, topic: str, round_number: int) -> str:
        """Generate a fallback argument when AI model fails"""
        
        fallback_templates = {
            "The Philosopher": [
                f"From an ethical standpoint, we must carefully examine the moral implications of {topic} and consider how it affects human dignity and our collective well-being.",
                f"The philosophical question we must ask about {topic} is: what does this mean for our understanding of justice, truth, and the good life?",
                f"History of philosophy teaches us that complex issues like {topic} require us to balance competing moral principles and consider long-term consequences."
            ],
            
            "The Scientist": [
                f"The evidence regarding {topic} requires rigorous analysis of peer-reviewed research and empirical data before we can reach valid conclusions.",
                f"From a scientific perspective, we need more controlled studies and data collection to fully understand the implications of {topic}.",
                f"The methodology for evaluating {topic} must be based on reproducible experiments and statistical significance."
            ],
            
            "The Advocate": [
                f"We must examine how {topic} impacts marginalized communities and ensure that justice and equality remain our guiding principles.",
                f"The human rights implications of {topic} cannot be ignored - we must protect the most vulnerable in our society.",
                f"Social justice demands that we consider {topic} through the lens of equity and fairness for all people."
            ],
            
            "The Pragmatist": [
                f"The practical implementation of policies regarding {topic} must consider cost-effectiveness, resource allocation, and real-world feasibility.",
                f"Let's focus on actionable solutions for {topic} that can be implemented efficiently and measured for success.",
                f"The bottom line on {topic} is what actually works in practice, not just what sounds good in theory."
            ],
            
            "The Contrarian": [
                f"Popular opinion about {topic} may be fundamentally misguided - we should question our assumptions and consider alternative perspectives.",
                f"The conventional wisdom regarding {topic} deserves skeptical examination. What if the majority view is wrong?",
                f"Before accepting mainstream conclusions about {topic}, let's challenge the underlying premises and explore contrarian viewpoints."
            ],
            
            "The Historian": [
                f"History shows us clear patterns regarding {topic} that we can learn from to avoid repeating past mistakes.",
                f"Looking at historical precedents for {topic}, we can see how similar situations have played out across different eras and cultures.",
                f"The lessons of history regarding {topic} remind us that those who ignore the past are doomed to repeat its errors."
            ]
        }
        
        templates = fallback_templates.get(personality.name, [
            f"This is an important topic that deserves thoughtful consideration from multiple perspectives, including the unique viewpoint I bring as {personality.name}."
        ])
        
        return random.choice(templates)
    
    def generate_judge_analysis(self, debate, winner: str = None) -> str:
        """Generate AI analysis for debate judging"""
        try:
            if not self.generator:
                return self._generate_fallback_judge_analysis(debate, winner)
            
            # Build prompt for judge analysis
            prompt = self._build_judge_prompt(debate)
            
            response = self.generator(
                prompt,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True,
                top_p=0.9
            )
            
            analysis = response[0]['generated_text'][len(prompt):].strip()
            analysis = self._clean_and_validate_argument(analysis)
            
            return analysis if analysis else self._generate_fallback_judge_analysis(debate, winner)
            
        except Exception as e:
            logger.error(f"Error generating judge analysis: {str(e)}")
            return self._generate_fallback_judge_analysis(debate, winner)
    
    def _build_judge_prompt(self, debate) -> str:
        """Build prompt for judge analysis"""
        arguments_summary = []
        for arg in debate.arguments[-6:]:  # Last 6 arguments
            arguments_summary.append(f"{arg['personality_id']}: {arg['content'][:100]}...")
        
        prompt = f"""You are an impartial debate judge evaluating arguments on: {debate.topic}

Key arguments presented:
{chr(10).join(arguments_summary)}

Provide a brief analysis of the debate quality and reasoning:"""
        
        return prompt
    
    def _generate_fallback_judge_analysis(self, debate, winner: str = None) -> str:
        """Generate fallback judge analysis"""
        if winner:
            return f"After careful consideration of all arguments presented on '{debate.topic}', {winner} presented the most compelling case with strong reasoning and evidence."
        else:
            return f"This debate on '{debate.topic}' featured diverse perspectives from all participants, each bringing unique insights and well-reasoned arguments."