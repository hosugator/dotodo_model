import json
import re
import os
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import BaseOutputParser
from langchain_community.callbacks import get_openai_callback

class JSONOutputParser(BaseOutputParser):
    """JSON 출력을 강제로 파싱하는 커스텀 파서"""
    
    def parse(self, text: str) -> Dict[str, Any]:
        """텍스트에서 JSON 부분을 추출하고 파싱"""
        try:
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx+1]
                return json.loads(json_str)
            
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            raise ValueError("JSON 형식을 찾을 수 없습니다.")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 오류: {e}")
    
    def get_format_instructions(self) -> str:
        return "응답은 반드시 유효한 JSON 형식으로만 주세요."

class LangChainTodoRecommendationSystem:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        
        # 최적화된 ChatOpenAI 설정
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model_name="gpt-4o-mini",
            temperature=0.5,
            max_tokens=600,
            timeout=15
        )
        
        self.json_parser = JSONOutputParser()
        self._setup_prompt_templates()
        self._setup_chains()
    
    def _setup_prompt_templates(self):
        """프롬프트 템플릿 설정"""
        
        # 최적화된 단일 프롬프트 템플릿
        self.single_prompt_template = PromptTemplate(
            input_variables=["p_data", "h_data"],
            template="""
You are a todo recommendation expert. Analyze user data and provide 3 final recommendations in a single step.

PAST WEEK COMPLETED TODOS:
{p_data}

TODAY'S SCHEDULED TODOS:
{h_data}

ANALYSIS PROCESS (think through this but only output final result):
1. Pattern Analysis: What categories does user complete frequently?
2. Gap Identification: What's missing from today's schedule?
3. Generate 10 candidate recommendations avoiding duplicates with today's todos
4. Select best 3 considering: feasibility, balance, user patterns

RULES:
- Categories: 운동, 공부, 장보기, 업무, 일상, 기타
- NO overlap with today's scheduled todos
- NO time/location details in parentheses
- Korean reason with **keyword** emphasis and warm tone

OUTPUT ONLY THIS JSON:
{{
    "final_recommendations": [
        {{"todo": "할일명", "category": "카테고리"}},
        {{"todo": "할일명", "category": "카테고리"}}, 
        {{"todo": "할일명", "category": "카테고리"}}
    ],
    "reason": "할일1은 **키워드**로 도움이 될 거예요. 할일2는 **키워드** 때문에 좋을 것 같아요. 할일3을 하시면 **키워드**가 향상될 거예요."
}}
"""
        )
    
    def _setup_chains(self):
        """체인 설정"""
        self.single_chain = self.single_prompt_template | self.llm | self.json_parser
    
    def _compress_past_data(self, p_data: List) -> str:
        """과거 데이터를 요약해서 프롬프트 크기 줄이기"""
        category_counts = {}
        recent_todos = []
        
        for day_data in p_data[-3:]:
            for category, todos in day_data['completed_todos'].items():
                category_counts[category] = category_counts.get(category, 0) + len(todos)
                for todo in todos[-2:]:
                    recent_todos.append(f"{category}: {todo['todo']}")
        
        compressed = {
            "patterns": category_counts,
            "recent_examples": recent_todos[-10:]
        }
        
        return json.dumps(compressed, ensure_ascii=False, indent=1)

    def _compress_today_data(self, h_data: Dict) -> str:
        """오늘 데이터 압축"""
        incomplete_todos = []
        completed_todos = []
        
        for category, todos in h_data['scheduled_todos'].items():
            for todo in todos:
                if todo['completed']:
                    completed_todos.append(f"{category}: {todo['todo']}")
                else:
                    incomplete_todos.append(f"{category}: {todo['todo']}")
        
        compressed = {
            "incomplete": incomplete_todos,
            "completed": completed_todos[:5]
        }
        
        return json.dumps(compressed, ensure_ascii=False, indent=1)
    
    def load_json_file(self, filename: str) -> Any:
        """JSON 파일 로드"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(current_dir, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {filename}")
            return None
        except json.JSONDecodeError:
            print(f"JSON 파싱 오류: {filename}")
            return None
    
    def save_json_file(self, data: Dict, filename: str) -> None:
        """JSON 파일 저장"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ {filename} 파일이 저장되었습니다.")
        except Exception as e:
            print(f"파일 저장 오류: {e}")
    
    def generate_final_output(self, second_result: Dict) -> Dict[str, Any]:
        """최종 출력 JSON 생성"""
        recommendations_without_reason = []
        
        for rec in second_result['final_recommendations']:
            recommendations_without_reason.append({
                "category": rec['category'],
                "todo": rec['todo'],
                "completed": False
            })
        
        overall_reason = second_result.get('reason', '추천 이유를 가져올 수 없습니다.')
    
        final_output = {
            "user_id": "user001",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "recommendations": recommendations_without_reason,
            "reason": overall_reason
        }
    
        return final_output
    
    def run_recommendation_process(self) -> Dict[str, Any]:
        """최적화된 단일 프롬프트 추천 프로세스"""
        print("=== 최적화된 Todo 추천 시스템 시작 ===")
        
        # 1. 데이터 로드
        print("1. 데이터 로딩...")
        combined_data = self.load_json_file('dummy_data.json')
        p_data = combined_data['p_data']
        h_data = combined_data['h_data']
        
        if not p_data or not h_data:
            print("❌ 데이터 로딩 실패")
            return {}
        
        print("✅ 데이터 로딩 완료")
        
        # 2. 데이터 압축
        p_data_compressed = self._compress_past_data(p_data)
        h_data_compressed = self._compress_today_data(h_data)
        
        # 3. 단일 프롬프트 실행
        print("\n2. 최적화된 추천 생성 중...")
        
        try:
            with get_openai_callback() as cb:
                single_result = self.single_chain.invoke({
                    "p_data": p_data_compressed,
                    "h_data": h_data_compressed
                })
                print(f"✅ 추천 생성 완료 - 토큰 사용: {cb.total_tokens}")
        except Exception as e:
            print(f"❌ 추천 생성 오류: {e}")
            return {}
        
        # 4. 결과 처리
        if not single_result or 'final_recommendations' not in single_result:
            print("❌ 추천 추출 실패")
            return {}
        
        print(f"✅ 최종 추천 {len(single_result['final_recommendations'])}개 추출")
        
        # 5. 최종 출력 생성
        print("\n3. 최종 출력 생성...")
        final_output = self.generate_final_output(single_result)
        
        # 6. 파일 저장
        print("\n4. 결과 저장...")
        self.save_json_file(final_output, 'final_recommendations.json')
        
        print("\n=== 최적화된 추천 시스템 완료 ===")
        return final_output