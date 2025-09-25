#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from todo_recommendation_system import LangChainTodoRecommendationSystem

def main():
    """간단한 최적화된 추천 시스템 테스트"""
    print("최적화된 Todo 추천 시스템 테스트")
    print("=" * 50)
    
    try:
        # 시스템 초기화
        system = LangChainTodoRecommendationSystem()
        print("✅ 시스템 초기화 완료")
        
        # 실행 시간 측정
        start_time = time.time()
        
        # 추천 생성
        result = system.run_recommendation_process()
        
        execution_time = time.time() - start_time
        
        # 결과 출력
        if result:
            print("\n" + "=" * 50)
            print("🎉 최종 결과:")
            print("=" * 50)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"\n⏱️ 실행 시간: {execution_time:.2f}초")
            print("✅ 추천 생성 완료!")
        else:
            print("❌ 추천 생성 실패")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()